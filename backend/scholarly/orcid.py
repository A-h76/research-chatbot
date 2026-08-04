"""ORCID Public API client (#26).

Responsibility: list public works for an ORCID iD and import into Library.
OA PDFs are resolved via DOI / PMID / PMCID / arXiv when present — ORCID itself
does not host PDFs. Non-OA → metadata stub (same honesty as PubMed).

Entry point only — no ORCID-specific analysis or evidence extraction.
OAuth / private works deferred.

Public API:
  search_works(query, page, per_page, db) → list[OrcidWork]  # query = ORCID iD
  get_work_by_id(work_id, db) → OrcidWork | None             # orcid:put-code
  download_open_access_pdf(work, *, max_bytes, db) → tuple[bytes, str] | None

Env:
  ENABLE_ORCID (default true)
  ORCID_BASE_URL — override for tests
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

import requests

from backend.scholarly import ProviderCache, get_or_fetch, provider_enabled, provider_get

logger = logging.getLogger(__name__)

_ORCID_BASE = os.environ.get("ORCID_BASE_URL", "https://pub.orcid.org/v3.0").rstrip("/")
_TIMEOUT = int(os.environ.get("ORCID_TIMEOUT", "12"))
_EMAIL = (
    os.environ.get("NCBI_EMAIL")
    or os.environ.get("CROSSREF_MAILTO")
    or "admin@dhund.com"
)
_VERSION = "v1"

# Canonical ORCID iD: 0000-0001-2345-6789 (checksum digit 0-9 or X)
_ORCID_RE = re.compile(
    r"(?:https?://(?:orcid\.org|sandbox\.orcid\.org)/)?"
    r"(?P<id>\d{4}-\d{4}-\d{4}-\d{3}[\dX])",
    re.I,
)


@dataclass
class OrcidWork:
    id: str = ""  # {orcid}:{put_code}
    orcid_id: str = ""
    put_code: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    citation_count: int = 0
    open_access_url: str = ""
    concepts: list[str] = field(default_factory=list)
    source: str = "orcid"
    is_open_access: bool = False
    pmid: str = ""
    pmcid: str = ""
    arxiv_id: str = ""


def normalize_orcid_id(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    m = _ORCID_RE.search(raw)
    if not m:
        # Bare 16 digits without dashes
        digits = re.sub(r"[^0-9Xx]", "", raw)
        if len(digits) == 16:
            body = digits.upper()
            return f"{body[0:4]}-{body[4:8]}-{body[8:12]}-{body[12:16]}"
        return ""
    return m.group("id").upper().replace("X", "X")  # keep X checksum


def external_item_id_for(orcid_id: str, put_code: str | int) -> str:
    oid = normalize_orcid_id(orcid_id)
    pc = str(put_code or "").strip()
    if not oid or not pc:
        return ""
    return f"{oid}:{pc}"[:120]


def parse_work_id(work_id: str | None) -> tuple[str, str]:
    """Split `{orcid}:{put_code}` → (orcid, put_code)."""
    raw = (work_id or "").strip()
    if ":" not in raw:
        return "", ""
    # ORCID itself contains dashes but not a colon; put-code is numeric.
    oid, _, rest = raw.partition(":")
    oid_n = normalize_orcid_id(oid)
    pc = rest.strip()
    if not oid_n or not pc.isdigit():
        return "", ""
    return oid_n, pc


def _orcid_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.orcid+json",
        "User-Agent": f"Dhund/1.0 (Research OS; mailto:{_EMAIL})",
    }


def _ext_ids(summary: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    block = summary.get("external-ids") or summary.get("externalIds") or {}
    items = block.get("external-id") or block.get("externalId") or []
    if isinstance(items, dict):
        items = [items]
    for item in items:
        if not isinstance(item, dict):
            continue
        typ = (
            item.get("external-id-type")
            or item.get("externalIdType")
            or ""
        ).strip().lower()
        val = (
            item.get("external-id-value")
            or item.get("externalIdValue")
            or ""
        ).strip()
        if typ and val and typ not in out:
            out[typ] = val
    return out


def _title_from_summary(summary: dict[str, Any]) -> str:
    title_block = summary.get("title") or {}
    if isinstance(title_block, dict):
        inner = title_block.get("title") or {}
        if isinstance(inner, dict):
            return (inner.get("value") or "").strip()
        return str(title_block.get("value") or "").strip()
    return str(title_block or "").strip()


def _year_from_summary(summary: dict[str, Any]) -> int | None:
    pub = summary.get("publication-date") or summary.get("publicationDate") or {}
    year_block = pub.get("year") or {}
    raw = year_block.get("value") if isinstance(year_block, dict) else year_block
    try:
        return int(str(raw)[:4]) if raw else None
    except (TypeError, ValueError):
        return None


def _venue_from_summary(summary: dict[str, Any]) -> str:
    jt = summary.get("journal-title") or summary.get("journalTitle") or {}
    if isinstance(jt, dict):
        return (jt.get("value") or "").strip()
    return str(jt or "").strip()


def _work_from_summary(summary: dict[str, Any], *, orcid_id: str) -> OrcidWork | None:
    put_code = summary.get("put-code") or summary.get("putCode")
    if put_code is None:
        return None
    pc = str(put_code).strip()
    ids = _ext_ids(summary)
    doi = (ids.get("doi") or "").strip().removeprefix("https://doi.org/")
    pmid = (ids.get("pmid") or ids.get("pubmed") or "").strip()
    pmcid = (ids.get("pmc") or ids.get("pmcid") or "").strip()
    if pmcid and not pmcid.upper().startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    arxiv_id = (ids.get("arxiv") or "").strip()
    title = _title_from_summary(summary)
    if not title and not doi and not pmid:
        return None
    return OrcidWork(
        id=external_item_id_for(orcid_id, pc),
        orcid_id=normalize_orcid_id(orcid_id),
        put_code=pc,
        doi=doi,
        title=title or (f"ORCID work {pc}"),
        year=_year_from_summary(summary),
        venue=_venue_from_summary(summary),
        pmid=pmid,
        pmcid=pmcid.upper() if pmcid else "",
        arxiv_id=arxiv_id,
        source="orcid",
    )


def _flatten_groups(payload: dict[str, Any], *, orcid_id: str) -> list[OrcidWork]:
    works: list[OrcidWork] = []
    for group in payload.get("group") or []:
        summaries = group.get("work-summary") or group.get("workSummary") or []
        if isinstance(summaries, dict):
            summaries = [summaries]
        # Prefer the first summary in each group (preferred / newest)
        for summary in summaries[:1]:
            if not isinstance(summary, dict):
                continue
            w = _work_from_summary(summary, orcid_id=orcid_id)
            if w:
                works.append(w)
                break
    return works


def _fetch_works_payload(orcid_id: str, *, db: Any) -> dict[str, Any] | None:
    oid = normalize_orcid_id(orcid_id)
    if not oid:
        return None
    cache = ProviderCache(db, "orcid")
    cache_key = f"works:{oid}"

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_ORCID_BASE}/{oid}/works",
            provider="orcid",
            endpoint="works",
            headers=_orcid_headers(),
            timeout=_TIMEOUT,
            db=db,
        )
        if not raw:
            return None
        return raw

    return get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=6,
        provider_version=_VERSION,
        endpoint="works",
        allow_stale=True,
        background_refresh=True,
    )


def enrich_oa_hints(work: OrcidWork, *, db: Any) -> OrcidWork:
    """Best-effort OA URL via OpenAlex DOI lookup. Soft-fails."""
    if work.open_access_url:
        work.is_open_access = True
        return work
    if work.arxiv_id:
        try:
            from backend.scholarly.arxiv import pdf_url_for

            url = pdf_url_for(work.arxiv_id)
            if url:
                work.open_access_url = url
                work.is_open_access = True
                return work
        except Exception:
            pass
    if not work.doi:
        return work
    try:
        from backend.scholarly.openalex import get_work_by_doi

        oa = get_work_by_doi(work.doi, db=db)
        if oa and oa.open_access_url:
            work.open_access_url = oa.open_access_url
            work.is_open_access = True
            if not work.title:
                work.title = oa.title
            if not work.authors:
                work.authors = oa.authors
            if not work.year and oa.year:
                work.year = oa.year
            if not work.abstract:
                work.abstract = oa.abstract
    except Exception as exc:
        logger.debug("orcid OA enrich skipped: %s", exc)
    return work


def search_works(
    query: str,
    *,
    page: int = 1,
    per_page: int = 15,
    db: Any,
    enrich: bool = True,
) -> list[OrcidWork]:
    """List public works for an ORCID iD (query must be / contain an ORCID)."""
    if not provider_enabled("orcid"):
        return []
    oid = normalize_orcid_id(query)
    if not oid:
        return []
    page = max(1, min(int(page or 1), 50))
    per_page = max(1, min(int(per_page or 15), 50))
    payload = _fetch_works_payload(oid, db=db)
    if not payload:
        return []
    works = _flatten_groups(payload, orcid_id=oid)
    start = (page - 1) * per_page
    chunk = works[start : start + per_page]
    if enrich:
        chunk = [enrich_oa_hints(w, db=db) for w in chunk]
    return chunk


def get_work_by_id(work_id: str, *, db: Any, enrich: bool = True) -> OrcidWork | None:
    oid, put_code = parse_work_id(work_id)
    if not oid or not put_code:
        # Allow bare ORCID — not a single work
        return None
    payload = _fetch_works_payload(oid, db=db)
    if not payload:
        return None
    for w in _flatten_groups(payload, orcid_id=oid):
        if w.put_code == put_code:
            return enrich_oa_hints(w, db=db) if enrich else w
    return None


def _looks_like_pdf(data: bytes, content_type: str) -> bool:
    if data[:4] == b"%PDF":
        return True
    ct = (content_type or "").lower()
    return "pdf" in ct and data[:4] == b"%PDF"


def download_open_access_pdf(
    work: OrcidWork,
    *,
    max_bytes: int = 50 * 1024 * 1024,
    db: Any = None,
) -> tuple[bytes, str] | None:
    """Resolve OA PDF via arXiv / DOI URL / Europe PMC / PubMed. Soft-fails to None."""
    work = enrich_oa_hints(work, db=db) if db is not None else work

    if work.arxiv_id:
        try:
            from backend.scholarly.arxiv import ArxivWork, download_pdf

            hit = download_pdf(
                ArxivWork(
                    id=work.arxiv_id,
                    arxiv_id=work.arxiv_id,
                    open_access_url=work.open_access_url,
                ),
                max_bytes=max_bytes,
            )
            if hit:
                return hit
        except Exception as exc:
            logger.debug("orcid arxiv pdf skipped: %s", exc)

    if work.pmid or work.pmcid:
        try:
            from backend.scholarly.europe_pmc import EuropePmcWork, download_open_access_pdf as epmc_dl

            hit = epmc_dl(
                EuropePmcWork(
                    id=work.pmcid or work.pmid,
                    pmid=work.pmid,
                    pmcid=work.pmcid,
                    open_access_url=work.open_access_url,
                    is_open_access=True,
                ),
                max_bytes=max_bytes,
            )
            if hit:
                return hit
        except Exception as exc:
            logger.debug("orcid epmc pdf skipped: %s", exc)

    url = (work.open_access_url or "").strip()
    if not url:
        return None
    headers = {
        "User-Agent": f"Dhund/1.0 (Research OS; mailto:{_EMAIL})",
        "Accept": "application/pdf,*/*",
    }
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
        if resp.status_code >= 400:
            return None
        ctype = (resp.headers.get("Content-Type") or "").lower()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        resp.close()
        data = b"".join(chunks)
        if data and _looks_like_pdf(data, ctype):
            label = work.put_code or "orcid"
            return data, f"orcid_{label}.pdf"
    except Exception as exc:
        logger.debug("orcid OA url download failed: %s", exc)
    return None
