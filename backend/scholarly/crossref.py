"""Crossref REST API integration.

Responsibilities (single):
  Verify and enrich paper metadata from a DOI.

Merge strategy (from product spec):
  - If existing field is empty → use Crossref value.
  - If DOI matches and titles are nearly identical (Levenshtein-normalised) → prefer Crossref.
  - Otherwise → keep original, log conflict.
  - Always record *_source columns so downstream can tell provenance.

Public API:
  enrich_file_from_doi(db, file_id) → bool   (True = enriched, False = skipped/failed)
  fetch_crossref_metadata(doi) → dict | None  (raw normalised fields)
  format_citation(doi, style, db) → dict      {citation, source, verified}

Called from:
  worker._handle_phase1_analysis  (async, never blocks upload)
  citations API endpoint          (with cache)
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from backend.scholarly import ProviderCache, provider_get

logger = logging.getLogger(__name__)

_CROSSREF_BASE = "https://api.crossref.org/v1"
_CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "admin@soro.app")
_CROSSREF_PLUS_TOKEN = os.environ.get("CROSSREF_PLUS_TOKEN", "")  # optional paid tier
_CROSSREF_TIMEOUT = int(os.environ.get("CROSSREF_TIMEOUT", "5"))
_CROSSREF_VERSION = "v1"


def _crossref_headers() -> dict[str, str]:
    h: dict[str, str] = {}
    if _CROSSREF_PLUS_TOKEN:
        h["Crossref-Plus-API-Token"] = f"Bearer {_CROSSREF_PLUS_TOKEN}"
    return h


def _crossref_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    p: dict[str, Any] = {"mailto": _CROSSREF_MAILTO}
    if extra:
        p.update(extra)
    return p


def _title_similarity(a: str, b: str) -> float:
    a = re.sub(r"\s+", " ", a.strip().lower())
    b = re.sub(r"\s+", " ", b.strip().lower())
    return SequenceMatcher(None, a, b).ratio()


def _normalise_authors(items: list[dict[str, Any]]) -> str:
    parts = []
    for item in items[:20]:
        family = item.get("family", "")
        given = item.get("given", "")
        if family and given:
            parts.append(f"{family}, {given[0]}.")
        elif family:
            parts.append(family)
    return "; ".join(parts)


def _extract_year(date_parts: list | None) -> str:
    if date_parts and isinstance(date_parts, list):
        parts = date_parts[0] if date_parts else []
        if parts and parts[0]:
            return str(parts[0])
    return ""


def _safe_str(val: Any, maxlen: int = 500) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        val = " ".join(str(v) for v in val)
    return str(val)[:maxlen]


def fetch_crossref_metadata(doi: str) -> dict[str, Any] | None:
    """Fetch and normalise Crossref metadata for a DOI.

    Returns a dict with keys: title, authors, year, venue, publisher,
    abstract, doi, source='crossref', or None on failure.
    """
    doi = doi.strip().lstrip("https://doi.org/").lstrip("http://doi.org/")
    if not doi:
        return None
    url = f"{_CROSSREF_BASE}/works/{doi}"
    raw = provider_get(
        url,
        params=_crossref_params(),
        headers=_crossref_headers(),
        timeout=_CROSSREF_TIMEOUT,
    )
    if not raw or raw.get("status") != "ok":
        return None
    msg = raw.get("message", {})
    if not isinstance(msg, dict):
        return None

    title_list = msg.get("title") or []
    title = _safe_str(title_list[0] if title_list else "", 500)
    authors = _normalise_authors(msg.get("author") or [])
    year = _extract_year(
        (msg.get("published-print") or msg.get("published-online") or {}).get("date-parts")
    )
    container = msg.get("container-title") or []
    venue = _safe_str(container[0] if container else "", 300)
    publisher = _safe_str(msg.get("publisher", ""), 300)
    abstract_raw = msg.get("abstract") or ""
    # Strip JATS XML tags if present
    abstract = re.sub(r"<[^>]+>", "", _safe_str(abstract_raw, 3000)).strip()

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "publisher": publisher,
        "abstract": abstract,
        "doi": doi,
        "source": "crossref",
        "crossref_type": _safe_str(msg.get("type", ""), 50),
    }


def enrich_file_from_doi(db: Any, file_id: int) -> bool:
    """Enrich a UserFile row from Crossref using its DOI.

    Called asynchronously from the worker after Phase 1.
    Applies the merge strategy: prefer Crossref when field is empty or
    when DOI confirmed and title is nearly identical.
    Never blocks user-visible operations.
    Returns True if any field was updated.
    """
    try:
        from sqlalchemy import text as sa_text

        row = db.execute(
            sa_text(
                "SELECT id, doi, title, authors, year, venue, abstract, "
                "doi_verified FROM files WHERE id=:fid LIMIT 1"
            ),
            {"fid": file_id},
        ).fetchone()
        if row is None:
            return False

        doi = (row[2 - 2] if False else None)  # re-read positionally below
        # Positional access is fragile; use fetchone as dict via mappings
        row = db.execute(
            sa_text(
                "SELECT id, doi, title, authors, year, venue, abstract, "
                "doi_verified FROM files WHERE id=:fid LIMIT 1"
            ),
            {"fid": file_id},
        ).mappings().fetchone()
        if row is None:
            return False

        doi = (row["doi"] or "").strip()
        if not doi:
            return False

        cache = ProviderCache(db, "crossref")
        data = cache.get(doi)
        if data is None:
            data = fetch_crossref_metadata(doi)
            if data:
                cache.set(doi, data, ttl_hours=168)  # 7 days
        if not data:
            return False

        existing_title = (row["title"] or "").strip()
        cx_title = (data.get("title") or "").strip()
        cx_authors = (data.get("authors") or "").strip()
        cx_year = str(data.get("year") or "").strip()
        cx_venue = (data.get("venue") or "").strip()
        cx_abstract = (data.get("abstract") or "").strip()

        updates: dict[str, Any] = {}
        sources: dict[str, str] = {}

        def _should_use(existing: str, crossref_val: str, field: str) -> bool:
            if not crossref_val:
                return False
            if not existing:
                return True
            if field == "title":
                sim = _title_similarity(existing, crossref_val)
                if sim >= 0.8:
                    return True
                logger.info(
                    "crossref metadata conflict file_id=%s field=%s sim=%.2f "
                    "existing=%r crossref=%r",
                    file_id, field, sim, existing[:60], crossref_val[:60],
                )
                return False
            return False  # for other fields: only fill empty

        if _should_use(existing_title, cx_title, "title"):
            updates["title"] = cx_title[:500]
            sources["title_source"] = "crossref"
        if _should_use(row["authors"] or "", cx_authors, "authors"):
            updates["authors"] = cx_authors[:1000]
            sources["authors_source"] = "crossref"
        if _should_use(row["year"] or "", cx_year, "year"):
            updates["year"] = cx_year[:10]
            sources["year_source"] = "crossref"
        if _should_use(row["venue"] or "", cx_venue, "venue"):
            updates["venue"] = cx_venue[:300]
            sources["venue_source"] = "crossref"
        if _should_use(row["abstract"] or "", cx_abstract, "abstract"):
            updates["abstract"] = cx_abstract[:3000]
            sources["abstract_source"] = "crossref"

        all_updates = {**updates, **sources,
                       "doi_verified": True,
                       "crossref_last_synced": datetime.now(timezone.utc),
                       "crossref_version": _CROSSREF_VERSION,
                       "metadata_source": "crossref"}

        if not all_updates:
            db.execute(
                sa_text(
                    "UPDATE files SET doi_verified=TRUE, crossref_last_synced=NOW(), "
                    "crossref_version=:v WHERE id=:fid"
                ),
                {"v": _CROSSREF_VERSION, "fid": file_id},
            )
            db.commit()
            return True

        set_clauses = ", ".join(f"{k}=:{k}" for k in all_updates)
        db.execute(
            sa_text(f"UPDATE files SET {set_clauses} WHERE id=:fid"),
            {**all_updates, "fid": file_id},
        )
        db.commit()
        logger.info(
            "crossref enriched file_id=%s fields=%s", file_id, list(updates.keys())
        )
        return True
    except Exception as exc:
        logger.warning("crossref enrich_file_from_doi failed file_id=%s: %s", file_id, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return False


# ── Citation formatting ───────────────────────────────────────────────────────

def _format_apa(m: dict[str, Any]) -> str:
    authors = m.get("authors") or ""
    year = m.get("year") or "n.d."
    title = m.get("title") or ""
    venue = m.get("venue") or ""
    doi = m.get("doi") or ""
    parts = []
    if authors:
        parts.append(f"{authors} ({year}).")
    elif year:
        parts.append(f"({year}).")
    if title:
        parts.append(f"{title}.")
    if venue:
        parts.append(f"*{venue}*.")
    if doi:
        parts.append(f"https://doi.org/{doi}")
    return " ".join(parts)


def _format_ieee(m: dict[str, Any]) -> str:
    authors = m.get("authors") or ""
    title = m.get("title") or ""
    venue = m.get("venue") or ""
    year = m.get("year") or ""
    doi = m.get("doi") or ""
    return (
        f"{authors}, \"{title},\" {venue}, {year}."
        + (f" doi: {doi}" if doi else "")
    )


def _format_bibtex(m: dict[str, Any]) -> str:
    key = re.sub(r"\W+", "", (m.get("authors") or "anon").split(",")[0].strip())
    year = m.get("year") or "0000"
    return (
        f"@article{{{key}{year},\n"
        f"  title   = {{{m.get('title', '')}}},\n"
        f"  author  = {{{m.get('authors', '')}}},\n"
        f"  journal = {{{m.get('venue', '')}}},\n"
        f"  year    = {{{year}}},\n"
        f"  doi     = {{{m.get('doi', '')}}}\n"
        f"}}"
    )


def _format_mla(m: dict[str, Any]) -> str:
    authors = m.get("authors") or ""
    title = m.get("title") or ""
    venue = m.get("venue") or ""
    year = m.get("year") or ""
    doi = m.get("doi") or ""
    return (
        f"{authors}. \"{title}.\" *{venue}* ({year})."
        + (f" https://doi.org/{doi}" if doi else "")
    )


_FORMATTERS = {
    "apa": _format_apa,
    "ieee": _format_ieee,
    "bibtex": _format_bibtex,
    "mla": _format_mla,
}


def format_citation(doi: str, style: str, db: Any) -> dict[str, Any]:
    """Return {citation, source, verified}.

    Tries Crossref first (cache then live); falls back to ai-formatted label.
    """
    style = style.lower().strip()
    doi = doi.strip().lstrip("https://doi.org/")
    formatter = _FORMATTERS.get(style)
    if not formatter or not doi:
        return {"citation": "", "source": "ai", "verified": False}

    cache = ProviderCache(db, "crossref")
    cache_key = f"citation:{doi}:{style}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    data = cache.get(doi)
    if data is None:
        data = fetch_crossref_metadata(doi)
        if data:
            cache.set(doi, data, ttl_hours=168)

    if not data:
        return {"citation": "", "source": "ai", "verified": False}

    citation_text = formatter(data)
    result = {"citation": citation_text, "source": "crossref", "verified": True}
    cache.set(cache_key, result, ttl_hours=168)
    return result
