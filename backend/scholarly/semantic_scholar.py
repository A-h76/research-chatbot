"""Semantic Scholar API integration.

Responsibility (single): related / recommended / citing papers for a given paper.

Public API:
  get_related_papers(file_id, doi_or_title, db) → RelatedPapersBundle | None

RelatedPapersBundle contains:
  - related:      semantically similar papers
  - citing:       papers that cite this one
  - recommended:  Semantic Scholar recommendations
  - cached_at, provider_version

Cache: 7 days per (file_id / doi).
Soft-fail: returns None when key absent or provider down; caller shows placeholder.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from backend.scholarly import ProviderCache, cache_key_hash, provider_get

logger = logging.getLogger(__name__)

_S2_BASE = "https://api.semanticscholar.org/graph/v1"
_S2_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", os.environ.get("S2_API_KEY", ""))
_S2_TIMEOUT = int(os.environ.get("S2_TIMEOUT", "5"))
_S2_VERSION = "2024-01"
_RELATED_TTL_HOURS = 7 * 24   # 7 days


def _s2_headers() -> dict[str, str]:
    if _S2_API_KEY:
        return {"x-api-key": _S2_API_KEY}
    return {}


_PAPER_FIELDS = "paperId,externalIds,title,authors,year,venue,citationCount,abstract,isOpenAccess,openAccessPdf"


@dataclass
class S2Paper:
    paper_id: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    citation_count: int = 0
    open_access_url: str = ""
    source: str = "semantic_scholar"


@dataclass
class RelatedPapersBundle:
    related: list[S2Paper] = field(default_factory=list)
    citing: list[S2Paper] = field(default_factory=list)
    recommended: list[S2Paper] = field(default_factory=list)
    provider_version: str = _S2_VERSION
    cached_at: str = ""


def _parse_s2_paper(item: dict[str, Any]) -> S2Paper:
    ext = item.get("externalIds") or {}
    doi = (ext.get("DOI") or "").strip()
    authors_list = [a.get("name") or "" for a in (item.get("authors") or [])[:10]]
    oa_pdf = (item.get("openAccessPdf") or {}).get("url") or ""
    return S2Paper(
        paper_id=item.get("paperId") or "",
        doi=doi,
        title=(item.get("title") or "").strip(),
        authors="; ".join(a for a in authors_list if a),
        year=item.get("year"),
        venue=(item.get("venue") or "").strip(),
        abstract=(item.get("abstract") or "").strip()[:800],
        citation_count=int(item.get("citationCount") or 0),
        open_access_url=oa_pdf,
    )


def _find_s2_paper_id(doi: str | None, title: str | None) -> str | None:
    """Resolve a Semantic Scholar paper ID from DOI or title."""
    if doi:
        raw = provider_get(
            f"{_S2_BASE}/paper/DOI:{doi}",
            params={"fields": "paperId"},
            headers=_s2_headers(),
            timeout=_S2_TIMEOUT,
        )
        if raw and raw.get("paperId"):
            return raw["paperId"]

    if title:
        raw = provider_get(
            f"{_S2_BASE}/paper/search",
            params={"query": title[:200], "limit": 1, "fields": "paperId,title"},
            headers=_s2_headers(),
            timeout=_S2_TIMEOUT,
        )
        if raw:
            data = raw.get("data") or []
            if data and data[0].get("paperId"):
                return data[0]["paperId"]
    return None


def _fetch_related(paper_id: str) -> list[S2Paper]:
    raw = provider_get(
        f"{_S2_BASE}/paper/{paper_id}/references",
        params={"fields": _PAPER_FIELDS, "limit": 10},
        headers=_s2_headers(),
        timeout=_S2_TIMEOUT,
    )
    if not raw:
        return []
    return [_parse_s2_paper(e.get("citedPaper") or {}) for e in (raw.get("data") or []) if e.get("citedPaper")]


def _fetch_citing(paper_id: str) -> list[S2Paper]:
    raw = provider_get(
        f"{_S2_BASE}/paper/{paper_id}/citations",
        params={"fields": _PAPER_FIELDS, "limit": 10, "sort": "year:desc"},
        headers=_s2_headers(),
        timeout=_S2_TIMEOUT,
    )
    if not raw:
        return []
    return [_parse_s2_paper(e.get("citingPaper") or {}) for e in (raw.get("data") or []) if e.get("citingPaper")]


def _fetch_recommended(paper_id: str) -> list[S2Paper]:
    raw = provider_get(
        f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{paper_id}",
        params={"fields": _PAPER_FIELDS, "limit": 10},
        headers=_s2_headers(),
        timeout=_S2_TIMEOUT,
    )
    if not raw:
        return []
    return [_parse_s2_paper(p) for p in (raw.get("recommendedPapers") or [])]


def get_related_papers(
    *,
    file_id: int,
    doi: str | None,
    title: str | None,
    db: Any,
) -> RelatedPapersBundle | None:
    """Fetch related, citing, and recommended papers.

    Returns None when Semantic Scholar is unavailable (key missing / rate limited).
    Always returns cached data if fresh (< 7 days).
    """
    if not _S2_API_KEY:
        logger.debug("SEMANTIC_SCHOLAR_API_KEY not set; skipping related papers")
        return None

    cache_key = f"related:file:{file_id}"
    cache = ProviderCache(db, "semantic_scholar")
    cached = cache.get(cache_key)
    if cached:
        try:
            bundle = RelatedPapersBundle(
                related=[S2Paper(**p) for p in cached.get("related", [])],
                citing=[S2Paper(**p) for p in cached.get("citing", [])],
                recommended=[S2Paper(**p) for p in cached.get("recommended", [])],
                provider_version=cached.get("provider_version", _S2_VERSION),
                cached_at=cached.get("cached_at", ""),
            )
            return bundle
        except Exception:
            pass

    doi = (doi or "").strip().lstrip("https://doi.org/") or None
    title = (title or "").strip() or None

    paper_id = _find_s2_paper_id(doi, title)
    if not paper_id:
        return None

    related = _fetch_related(paper_id)
    citing = _fetch_citing(paper_id)
    recommended = _fetch_recommended(paper_id)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    bundle = RelatedPapersBundle(
        related=related,
        citing=citing,
        recommended=recommended,
        cached_at=now,
    )

    cache.set(
        cache_key,
        {
            "related": [p.__dict__ for p in related],
            "citing": [p.__dict__ for p in citing],
            "recommended": [p.__dict__ for p in recommended],
            "provider_version": _S2_VERSION,
            "cached_at": now,
        },
        ttl_hours=_RELATED_TTL_HOURS,
    )
    return bundle
