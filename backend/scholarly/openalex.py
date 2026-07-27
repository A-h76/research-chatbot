"""OpenAlex API integration.

Responsibility (single): discover papers by keyword search.

Public API:
  search_works(query, page, per_page, db) → list[OpenAlexWork]
  get_work_by_doi(doi, db)               → OpenAlexWork | None

OpenAlexWork is a plain dataclass — no ORM, no Flask imports.
Provenance: source='openalex' on every result.

Rate/cache:
  Search results cached 30 min (query-hash keyed).
  DOI lookups cached 7 days.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from backend.scholarly import ProviderCache, provider_get

logger = logging.getLogger(__name__)

_OPENALEX_BASE = "https://api.openalex.org"
_OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "")
_OPENALEX_TIMEOUT = int(os.environ.get("OPENALEX_TIMEOUT", "5"))
_OPENALEX_EMAIL = os.environ.get("CROSSREF_MAILTO", "admin@soro.app")


def _params(**extra: Any) -> dict[str, Any]:
    p: dict[str, Any] = {"mailto": _OPENALEX_EMAIL}
    if _OPENALEX_API_KEY:
        p["api_key"] = _OPENALEX_API_KEY
    p.update(extra)
    return p


@dataclass
class OpenAlexWork:
    id: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    citation_count: int = 0
    open_access_url: str = ""
    concepts: list[str] = field(default_factory=list)
    source: str = "openalex"


def _parse_work(item: dict[str, Any]) -> OpenAlexWork:
    doi_raw = (item.get("doi") or "").replace("https://doi.org/", "").strip()
    title = (item.get("title") or "").strip()

    authorships = item.get("authorships") or []
    authors_list = []
    for a in authorships[:10]:
        author = a.get("author") or {}
        name = author.get("display_name") or ""
        if name:
            authors_list.append(name)
    authors = "; ".join(authors_list)

    # Abstract from inverted index (OpenAlex format)
    abstract_inv = item.get("abstract_inverted_index")
    abstract = ""
    if abstract_inv and isinstance(abstract_inv, dict):
        positions: list[tuple[int, str]] = []
        for word, locs in abstract_inv.items():
            for loc in locs:
                positions.append((loc, word))
        positions.sort()
        abstract = " ".join(w for _, w in positions[:200])

    best_oa = item.get("best_oa_location") or {}
    oa_url = (best_oa.get("pdf_url") or best_oa.get("landing_page_url") or "").strip()

    concepts = [
        (c.get("display_name") or "")
        for c in (item.get("concepts") or [])[:8]
        if c.get("display_name")
    ]

    venue_data = item.get("primary_location") or {}
    source_data = venue_data.get("source") or {}
    venue = (source_data.get("display_name") or "").strip()

    pub_year = item.get("publication_year")

    return OpenAlexWork(
        id=item.get("id") or "",
        doi=doi_raw,
        title=title,
        authors=authors,
        year=int(pub_year) if pub_year else None,
        venue=venue,
        abstract=abstract[:1000],
        citation_count=int(item.get("cited_by_count") or 0),
        open_access_url=oa_url,
        concepts=concepts,
    )


def search_works(
    query: str,
    *,
    page: int = 1,
    per_page: int = 15,
    db: Any,
) -> list[OpenAlexWork]:
    """Search OpenAlex by keyword.  Returns up to per_page results."""
    query = query.strip()
    if not query:
        return []

    cache_key = hashlib.sha256(f"search:{query}:{page}:{per_page}".encode()).hexdigest()[:48]
    cache = ProviderCache(db, "openalex")
    cached = cache.get(cache_key)
    if cached:
        return [OpenAlexWork(**w) for w in cached.get("works", [])]

    raw = provider_get(
        f"{_OPENALEX_BASE}/works",
        params=_params(
            search=query,
            per_page=min(per_page, 25),
            page=page,
            select=(
                "id,doi,title,authorships,publication_year,"
                "primary_location,abstract_inverted_index,"
                "cited_by_count,best_oa_location,concepts"
            ),
        ),
        timeout=_OPENALEX_TIMEOUT,
    )
    if not raw:
        return []

    results = [_parse_work(item) for item in (raw.get("results") or [])]
    cache.set(cache_key, {"works": [w.__dict__ for w in results]}, ttl_hours=1)
    return results


def get_work_by_doi(doi: str, *, db: Any) -> OpenAlexWork | None:
    """Fetch a single work by DOI."""
    doi = doi.strip().lstrip("https://doi.org/")
    if not doi:
        return None
    cache_key = f"doi:{doi}"
    cache = ProviderCache(db, "openalex")
    cached = cache.get(cache_key)
    if cached and cached.get("id"):
        return OpenAlexWork(**cached)

    raw = provider_get(
        f"{_OPENALEX_BASE}/works/https://doi.org/{doi}",
        params=_params(
            select=(
                "id,doi,title,authorships,publication_year,"
                "primary_location,abstract_inverted_index,"
                "cited_by_count,best_oa_location,concepts"
            )
        ),
        timeout=_OPENALEX_TIMEOUT,
    )
    if not raw or not raw.get("id"):
        return None
    work = _parse_work(raw)
    cache.set(cache_key, work.__dict__, ttl_hours=168)
    return work
