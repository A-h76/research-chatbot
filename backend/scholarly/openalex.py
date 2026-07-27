"""OpenAlex API integration.

Responsibility (single): discover papers by keyword search.

Public API:
  search_works(query, page, per_page, db) → list[OpenAlexWork]
  get_work_by_doi(doi, db)               → OpenAlexWork | None

No API key required for normal use. Optional OPENALEX_BASE_URL override.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from backend.scholarly import ProviderCache, get_or_fetch, provider_get

logger = logging.getLogger(__name__)

_OPENALEX_BASE = os.environ.get("OPENALEX_BASE_URL", "https://api.openalex.org").rstrip("/")
_OPENALEX_TIMEOUT = int(os.environ.get("OPENALEX_TIMEOUT", "5"))
_OPENALEX_EMAIL = os.environ.get("CROSSREF_MAILTO", "admin@soro.app")
_OPENALEX_VERSION = "v1"


def _params(**extra: Any) -> dict[str, Any]:
    p: dict[str, Any] = {"mailto": _OPENALEX_EMAIL}
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
    """Search OpenAlex by keyword. Cached 30 min; stale-while-revalidate."""
    query = query.strip()
    if not query:
        return []

    cache_key = hashlib.sha256(
        f"search:{query.lower()}:{page}:{per_page}".encode()
    ).hexdigest()[:48]
    cache = ProviderCache(db, "openalex")

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_OPENALEX_BASE}/works",
            provider="openalex",
            endpoint="works/search",
            params=_params(
                search=query,
                per_page=min(per_page, 20),
                page=page,
                select=(
                    "id,doi,title,authorships,publication_year,"
                    "primary_location,abstract_inverted_index,"
                    "cited_by_count,best_oa_location,concepts"
                ),
            ),
            timeout=_OPENALEX_TIMEOUT,
            db=db,
        )
        if not raw:
            return None
        results = [_parse_work(item) for item in (raw.get("results") or [])]
        return {"works": [w.__dict__ for w in results]}

    cached = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=1,  # 30–60 min band; 1h is fine for Discover
        provider_version=_OPENALEX_VERSION,
        endpoint="works/search",
        allow_stale=True,
        background_refresh=True,
    )
    if not cached:
        return []
    return [OpenAlexWork(**w) for w in cached.get("works", [])]


def get_work_by_doi(doi: str, *, db: Any) -> OpenAlexWork | None:
    """Fetch a single work by DOI."""
    doi = doi.strip().removeprefix("https://doi.org/")
    if not doi:
        return None
    cache_key = f"doi:{doi}"
    cache = ProviderCache(db, "openalex")

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_OPENALEX_BASE}/works/https://doi.org/{doi}",
            provider="openalex",
            endpoint="works/doi",
            params=_params(
                select=(
                    "id,doi,title,authorships,publication_year,"
                    "primary_location,abstract_inverted_index,"
                    "cited_by_count,best_oa_location,concepts"
                )
            ),
            timeout=_OPENALEX_TIMEOUT,
            db=db,
        )
        if not raw or not raw.get("id"):
            return None
        return _parse_work(raw).__dict__

    cached = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=168,
        provider_version=_OPENALEX_VERSION,
        endpoint="works/doi",
        allow_stale=True,
        background_refresh=True,
    )
    if not cached or not cached.get("id"):
        return None
    return OpenAlexWork(**cached)
