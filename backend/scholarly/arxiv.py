"""arXiv API integration.

Responsibility: preprint discovery by keyword / arXiv id, with PDF download
for Golden Rule import (Library → Analysis → Evidence).

Public API:
  search_works(query, page, per_page, db) → list[ArxivWork]
  get_work_by_id(arxiv_id, db) → ArxivWork | None
  download_pdf(work, *, max_bytes) → tuple[bytes, str] | None

Env:
  ENABLE_ARXIV (default true)
  ARXIV_BASE_URL — Atom API override (tests)
  ARXIV_PDF_BASE — PDF URL override
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import requests

from backend.scholarly import (
    ProviderCache,
    circuit_is_open,
    circuit_record_failure,
    circuit_record_success,
    get_or_fetch,
    provider_enabled,
    record_metric,
    _bulkhead_acquire,
    _bulkhead_release,
)

logger = logging.getLogger(__name__)

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_API = os.environ.get("ARXIV_BASE_URL", "https://export.arxiv.org/api/query").rstrip("?")
_PDF_BASE = os.environ.get("ARXIV_PDF_BASE", "https://arxiv.org/pdf").rstrip("/")
_TIMEOUT = int(os.environ.get("ARXIV_TIMEOUT", "12"))
_EMAIL = os.environ.get("CROSSREF_MAILTO") or os.environ.get("NCBI_EMAIL") or "admin@dhund.com"
_VERSION = "v1"

# New-style 2107.12345 or 2107.12345v1; legacy hep-th/9901001
_ARXIV_ID_RE = re.compile(
    r"^(?:arXiv:)?(?:(?P<legacy>[a-z\-]+(?:\.[A-Z]{2})?/\d{7})|(?P<new>\d{4}\.\d{4,5}))(?:v\d+)?$",
    re.I,
)


@dataclass
class ArxivWork:
    id: str = ""  # normalized arxiv id without version
    arxiv_id: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    venue: str = "arXiv"
    abstract: str = ""
    citation_count: int = 0
    open_access_url: str = ""
    concepts: list[str] = field(default_factory=list)
    source: str = "arxiv"
    is_open_access: bool = True
    primary_category: str = ""


def normalize_arxiv_id(value: str | None) -> str:
    raw = (value or "").strip()
    raw = re.sub(r"(?i)^arXiv:\s*", "", raw).strip()
    # Strip version suffix for identity
    raw = re.sub(r"v\d+$", "", raw, flags=re.I).strip()
    # URL forms
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^?\s#]+)", raw, re.I)
    if m:
        raw = m.group(1).removesuffix(".pdf")
        raw = re.sub(r"v\d+$", "", raw, flags=re.I)
    if not raw:
        return ""
    match = _ARXIV_ID_RE.match(raw)
    if not match:
        # Allow bare new-style without full regex edge cases
        if re.match(r"^\d{4}\.\d{4,5}$", raw):
            return raw
        if re.match(r"^[a-z\-]+(?:\.[A-Z]{2})?/\d{7}$", raw, re.I):
            return raw
        return ""
    return (match.group("new") or match.group("legacy") or "").strip()


def pdf_url_for(arxiv_id: str) -> str:
    aid = normalize_arxiv_id(arxiv_id)
    if not aid:
        return ""
    return f"{_PDF_BASE}/{aid}.pdf"


def _atom_text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return " ".join(el.text.split()).strip()


def _parse_entry(entry: ET.Element) -> ArxivWork | None:
    id_url = _atom_text(entry.find("atom:id", _ATOM_NS))
    aid = normalize_arxiv_id(id_url)
    if not aid:
        # fallback: last path segment
        aid = normalize_arxiv_id(id_url.rsplit("/", 1)[-1] if id_url else "")
    if not aid:
        return None

    title = _atom_text(entry.find("atom:title", _ATOM_NS))
    summary = _atom_text(entry.find("atom:summary", _ATOM_NS))
    published = _atom_text(entry.find("atom:published", _ATOM_NS))
    year = None
    if published and len(published) >= 4 and published[:4].isdigit():
        year = int(published[:4])

    authors = []
    for a in entry.findall("atom:author", _ATOM_NS)[:20]:
        name = _atom_text(a.find("atom:name", _ATOM_NS))
        if name:
            authors.append(name)

    doi = ""
    for link in entry.findall("atom:link", _ATOM_NS):
        href = (link.get("href") or "").strip()
        title_attr = (link.get("title") or "").lower()
        if "doi.org" in href.lower():
            doi = href.split("doi.org/", 1)[-1].strip()
        if title_attr == "doi" and href:
            doi = href.replace("http://dx.doi.org/", "").replace("https://doi.org/", "")

    doi_el = entry.find("arxiv:doi", _ATOM_NS)
    if doi_el is not None and (doi_el.text or "").strip():
        doi = (doi_el.text or "").strip()

    cats = []
    primary = ""
    primary_el = entry.find("arxiv:primary_category", _ATOM_NS)
    if primary_el is not None:
        primary = (primary_el.get("term") or "").strip()
        if primary:
            cats.append(primary)
    for c in entry.findall("atom:category", _ATOM_NS):
        term = (c.get("term") or "").strip()
        if term and term not in cats:
            cats.append(term)

    return ArxivWork(
        id=aid,
        arxiv_id=aid,
        doi=doi,
        title=title,
        authors="; ".join(authors),
        year=year,
        venue="arXiv",
        abstract=summary[:4000],
        open_access_url=pdf_url_for(aid),
        concepts=cats[:8],
        primary_category=primary,
        is_open_access=True,
        source="arxiv",
    )


def _fetch_atom(params: dict[str, Any], *, db: Any, endpoint: str) -> str | None:
    """GET Atom XML with scholarly bulkhead/circuit/metrics. Soft-fails to None."""
    if not provider_enabled("arxiv"):
        record_metric(db, provider="arxiv", endpoint=endpoint, latency_ms=0, status="disabled")
        return None
    if circuit_is_open("arxiv", db):
        record_metric(db, provider="arxiv", endpoint=endpoint, latency_ms=0, status="circuit_open")
        return None
    if not _bulkhead_acquire("arxiv"):
        record_metric(db, provider="arxiv", endpoint=endpoint, latency_ms=0, status="bulkhead_full")
        return None

    import time

    started = time.monotonic()
    try:
        headers = {
            "User-Agent": f"Dhund/1.0 (Research OS; mailto:{_EMAIL})",
            "Accept": "application/atom+xml, application/xml, text/xml, */*",
        }
        resp = requests.get(_API, params=params, headers=headers, timeout=_TIMEOUT)
        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code == 429:
            circuit_record_failure("arxiv", db)
            record_metric(db, provider="arxiv", endpoint=endpoint, latency_ms=latency, status="rate_limited")
            return None
        resp.raise_for_status()
        circuit_record_success("arxiv", db)
        record_metric(db, provider="arxiv", endpoint=endpoint, latency_ms=latency, status="ok")
        return resp.text
    except Exception as exc:
        latency = int((time.monotonic() - started) * 1000)
        logger.warning("arxiv atom fetch failed: %s", exc)
        circuit_record_failure("arxiv", db)
        record_metric(db, provider="arxiv", endpoint=endpoint, latency_ms=latency, status="error")
        return None
    finally:
        _bulkhead_release("arxiv")


def _parse_feed(xml_text: str) -> list[ArxivWork]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("arxiv atom parse failed: %s", exc)
        return []
    works: list[ArxivWork] = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        w = _parse_entry(entry)
        if w:
            works.append(w)
    return works


def _looks_like_id_query(query: str) -> str:
    """Return normalized arXiv id if the whole query is an id / abs URL."""
    q = (query or "").strip()
    if "arxiv.org/" in q.lower():
        return normalize_arxiv_id(q)
    cleaned = re.sub(r"(?i)^arXiv:\s*", "", q).strip()
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", cleaned):
        return normalize_arxiv_id(cleaned)
    if re.match(r"^[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(v\d+)?$", cleaned, re.I):
        return normalize_arxiv_id(cleaned)
    return ""


def search_works(
    query: str,
    *,
    page: int = 1,
    per_page: int = 15,
    db: Any,
) -> list[ArxivWork]:
    query = (query or "").strip()
    if not query:
        return []

    page = max(1, int(page))
    per_page = min(20, max(1, int(per_page)))
    start = (page - 1) * per_page

    aid = _looks_like_id_query(query)
    if aid:
        work = get_work_by_id(aid, db=db)
        return [work] if work else []

    cache = ProviderCache(db, "arxiv")
    cache_key = hashlib.sha256(
        f"search:{query.lower()}:{page}:{per_page}".encode()
    ).hexdigest()[:48]

    def _fetch() -> dict[str, Any] | None:
        search_query = query
        if not search_query.lower().startswith(("all:", "ti:", "au:", "abs:", "cat:", "id:")):
            search_query = f"all:{query}"
        xml_text = _fetch_atom(
            {
                "search_query": search_query,
                "start": start,
                "max_results": per_page,
                "sortBy": "relevance",
                "sortOrder": "descending",
            },
            db=db,
            endpoint="query/search",
        )
        if not xml_text:
            return None
        works = _parse_feed(xml_text)
        return {"works": [w.__dict__ for w in works]}

    cached = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=1,
        provider_version=_VERSION,
        endpoint="query/search",
        allow_stale=True,
        background_refresh=True,
    )
    if not cached:
        return []
    return [ArxivWork(**w) for w in cached.get("works", [])]


def get_work_by_id(arxiv_id: str, *, db: Any) -> ArxivWork | None:
    aid = normalize_arxiv_id(arxiv_id)
    if not aid:
        return None
    cache = ProviderCache(db, "arxiv")
    cache_key = f"id:{aid}"

    def _fetch() -> dict[str, Any] | None:
        xml_text = _fetch_atom(
            {
                "id_list": aid,
                "max_results": 1,
            },
            db=db,
            endpoint="query/id",
        )
        if not xml_text:
            return None
        works = _parse_feed(xml_text)
        if not works:
            return {"empty": True}
        return works[0].__dict__

    cached = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=168,
        provider_version=_VERSION,
        endpoint="query/id",
        allow_stale=True,
        background_refresh=True,
    )
    if not cached or cached.get("empty") or not cached.get("id"):
        return None
    return ArxivWork(**{k: v for k, v in cached.items() if k != "empty"})


def download_pdf(
    work: ArxivWork,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str] | None:
    """Download arXiv PDF. Soft-fails to None."""
    url = (work.open_access_url or "").strip() or pdf_url_for(work.arxiv_id or work.id)
    if not url:
        return None
    headers = {
        "User-Agent": f"Dhund/1.0 (Research OS; mailto:{_EMAIL})",
        "Accept": "application/pdf,*/*",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=_TIMEOUT, allow_redirects=True, stream=True)
        if resp.status_code >= 400:
            return None
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
        if not data or data[:4] != b"%PDF":
            return None
        aid = work.arxiv_id or work.id or "unknown"
        safe = aid.replace("/", "_")
        return data, f"arXiv_{safe}.pdf"
    except Exception as exc:
        logger.debug("arxiv pdf download failed: %s", exc)
        return None
