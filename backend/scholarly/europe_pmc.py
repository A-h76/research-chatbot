"""Europe PMC scholarly client (#25).

Responsibility: biomedical discovery by keyword / PMCID / PMID, with OA PDF
download for Golden Rule import (Library → Analysis → Evidence → Writing).

Entry point only — no Europe-PMC-specific analysis or evidence extraction.

Public API:
  search_works(query, page, per_page, db) → list[EuropePmcWork]
  get_work_by_id(work_id, db) → EuropePmcWork | None
  download_open_access_pdf(work, *, max_bytes) → tuple[bytes, str] | None

Env:
  ENABLE_EUROPE_PMC (default true)
  EUROPEPMC_BASE_URL — override for tests
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests

from backend.scholarly import ProviderCache, get_or_fetch, provider_enabled, provider_get

logger = logging.getLogger(__name__)

_EUROPEPMC = os.environ.get(
    "EUROPEPMC_BASE_URL", "https://www.ebi.ac.uk/europepmc/webservices/rest"
).rstrip("/")
_TIMEOUT = int(os.environ.get("EUROPEPMC_TIMEOUT", "10"))
_EMAIL = (
    os.environ.get("NCBI_EMAIL")
    or os.environ.get("CROSSREF_MAILTO")
    or "admin@dhund.com"
)
_VERSION = "v1"

_PMID_RE = re.compile(r"^\d{1,12}$")
_PMCID_RE = re.compile(r"^(?:PMC)?(\d+)$", re.I)


@dataclass
class EuropePmcWork:
    id: str = ""  # stable Discover card key (prefer PMCID, else MED:pmid)
    pmid: str = ""
    pmcid: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    citation_count: int = 0
    open_access_url: str = ""
    concepts: list[str] = field(default_factory=list)
    source: str = "europe_pmc"
    is_open_access: bool = False
    epmc_source: str = ""  # MED, PMC, etc.


def normalize_pmid(value: str | int | None) -> str:
    raw = str(value or "").strip()
    raw = re.sub(r"(?i)^pmid[:\s]*", "", raw).strip()
    if not _PMID_RE.match(raw):
        return ""
    return str(int(raw))


def normalize_pmcid(value: str | None) -> str:
    raw = (value or "").strip()
    raw = re.sub(r"(?i)^pmcid[:\s]*", "", raw).strip()
    m = _PMCID_RE.match(raw)
    if not m:
        return ""
    return f"PMC{m.group(1)}"


def normalize_europe_pmc_id(value: str | None) -> str:
    """Return PMCID, bare PMID, or MED:{pmid} for identity / lookup."""
    raw = (value or "").strip()
    if not raw:
        return ""
    m = re.search(r"europepmc\.org/article/([A-Z]+)/([^/?#\s]+)", raw, re.I)
    if m:
        src, eid = m.group(1).upper(), m.group(2).strip()
        if src == "PMC":
            return normalize_pmcid(eid) or normalize_pmcid(f"PMC{eid}")
        if src == "MED":
            return normalize_pmid(eid) or eid
        return f"{src}:{eid}"
    pmc = normalize_pmcid(raw)
    if pmc:
        return pmc
    if raw.upper().startswith("MED:"):
        return normalize_pmid(raw.split(":", 1)[-1]) or raw
    pmid = normalize_pmid(raw)
    if pmid:
        return pmid
    return ""


def external_item_id_for(work: EuropePmcWork) -> str:
    if work.pmcid:
        return work.pmcid
    if work.pmid:
        return f"MED:{work.pmid}"
    return (work.id or "")[:120]


def _pdf_url_from_hit(hit: dict[str, Any], *, pmcid: str, is_oa: bool) -> str:
    pdf_url = ""
    for u in hit.get("fullTextUrlList", {}).get("fullTextUrl") or []:
        docstyle = (u.get("documentStyle") or "").lower()
        avail = (u.get("availabilityCode") or u.get("availability") or "").lower()
        url = (u.get("url") or "").strip()
        if not url:
            continue
        if docstyle == "pdf" or url.lower().endswith(".pdf"):
            if avail in ("oa", "free", "") or is_oa:
                pdf_url = url
                break
        if not pdf_url and docstyle in ("html", "doi") and is_oa:
            pdf_url = url
    if not pdf_url and pmcid and is_oa:
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    return pdf_url


def _work_from_hit(hit: dict[str, Any]) -> EuropePmcWork:
    pmid = normalize_pmid(hit.get("pmid") or "")
    if not pmid and str(hit.get("source") or "").upper() == "MED":
        pmid = normalize_pmid(hit.get("id") or "")
    pmcid = normalize_pmcid(hit.get("pmcid") or "")
    doi = (hit.get("doi") or "").strip().removeprefix("https://doi.org/")
    year_raw = hit.get("pubYear") or hit.get("year") or ""
    year = None
    try:
        year = int(str(year_raw)[:4]) if year_raw else None
    except (TypeError, ValueError):
        year = None
    is_oa = str(hit.get("isOpenAccess") or "").lower() in ("y", "yes", "true", "1")
    pdf_url = _pdf_url_from_hit(hit, pmcid=pmcid, is_oa=is_oa)
    if pdf_url:
        is_oa = True
    epmc_source = str(hit.get("source") or "").upper()
    if pmcid:
        card_id = pmcid
    elif pmid:
        card_id = f"MED:{pmid}"
    else:
        card_id = f"{epmc_source}:{hit.get('id') or ''}".strip(":")

    mesh: list[str] = []
    for m in hit.get("meshHeadingList", {}).get("meshHeading") or []:
        label = (m.get("descriptorName") or "").strip()
        if label:
            mesh.append(label)

    cited = hit.get("citedByCount")
    try:
        citation_count = int(cited or 0)
    except (TypeError, ValueError):
        citation_count = 0

    return EuropePmcWork(
        id=card_id,
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        title=(hit.get("title") or "").strip(),
        authors=(hit.get("authorString") or "").strip(),
        year=year,
        venue=(hit.get("journalTitle") or "").strip(),
        abstract=(hit.get("abstractText") or "").strip()[:4000],
        citation_count=citation_count,
        open_access_url=pdf_url,
        concepts=mesh[:8],
        source="europe_pmc",
        is_open_access=is_oa,
        epmc_source=epmc_source,
    )


def _lookup_query_for_id(work_id: str) -> str | None:
    aid = normalize_europe_pmc_id(work_id)
    if not aid:
        return None
    pmc = normalize_pmcid(aid)
    if pmc:
        return f"PMCID:{pmc}"
    pmid = normalize_pmid(aid)
    if pmid:
        return f"EXT_ID:{pmid} AND SRC:MED"
    if ":" in aid:
        src, eid = aid.split(":", 1)
        return f"EXT_ID:{eid} AND SRC:{src}"
    return None


def _search_api(
    query: str,
    *,
    page: int,
    per_page: int,
    db: Any,
) -> list[EuropePmcWork]:
    cache = ProviderCache(db, "europe_pmc")
    cache_key = hashlib.sha256(
        f"search:{query}:p{page}:n{per_page}".encode()
    ).hexdigest()[:48]

    def _fetch() -> dict[str, Any] | None:
        cursor = "*"
        # Walk cursors for page > 1 (Europe PMC dropped numeric page).
        for _ in range(max(1, page)):
            raw = provider_get(
                f"{_EUROPEPMC}/search",
                provider="europe_pmc",
                endpoint="search",
                params={
                    "query": query,
                    "format": "json",
                    "resultType": "core",
                    "pageSize": per_page,
                    "cursorMark": cursor,
                },
                timeout=_TIMEOUT,
                db=db,
            )
            if not raw:
                return None
            if page == 1 or _ == page - 1:
                return raw
            cursor = (raw.get("nextCursorMark") or "").strip()
            if not cursor or cursor == "*":
                return {"resultList": {"result": []}}
        return None

    raw = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=6,
        provider_version=_VERSION,
        endpoint="search",
        allow_stale=True,
        background_refresh=True,
    )
    if not raw:
        return []
    hits = ((raw.get("resultList") or {}).get("result")) or []
    return [_work_from_hit(h) for h in hits if isinstance(h, dict)]


def search_works(
    query: str,
    *,
    page: int = 1,
    per_page: int = 15,
    db: Any,
) -> list[EuropePmcWork]:
    if not provider_enabled("europe_pmc"):
        return []
    q = (query or "").strip()
    if not q:
        return []
    page = max(1, min(int(page or 1), 20))
    per_page = max(1, min(int(per_page or 15), 50))

    # Direct id / URL shortcut
    lookup = _lookup_query_for_id(q)
    if lookup and normalize_europe_pmc_id(q):
        hit = get_work_by_id(q, db=db)
        return [hit] if hit else []

    return _search_api(q, page=page, per_page=per_page, db=db)


def get_work_by_id(work_id: str, *, db: Any) -> EuropePmcWork | None:
    if not provider_enabled("europe_pmc"):
        return None
    lookup = _lookup_query_for_id(work_id)
    if not lookup:
        return None
    cache = ProviderCache(db, "europe_pmc")
    cache_key = f"id:{normalize_europe_pmc_id(work_id)}"

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_EUROPEPMC}/search",
            provider="europe_pmc",
            endpoint="get",
            params={
                "query": lookup,
                "format": "json",
                "resultType": "core",
                "pageSize": 1,
            },
            timeout=_TIMEOUT,
            db=db,
        )
        if not raw:
            return None
        results = ((raw.get("resultList") or {}).get("result")) or []
        if not results:
            return {"empty": True}
        return results[0]

    hit = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=24,
        provider_version=_VERSION,
        endpoint="get",
        allow_stale=True,
        background_refresh=True,
    )
    if not hit or hit.get("empty"):
        return None
    return _work_from_hit(hit)


def _looks_like_pdf(data: bytes, content_type: str) -> bool:
    if data[:4] == b"%PDF":
        return True
    ct = (content_type or "").lower()
    return "pdf" in ct and data[:4] == b"%PDF"


def download_open_access_pdf(
    work: EuropePmcWork,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str] | None:
    """Legacy/internal OA download — not the acquisition API.

    New code: ``backend.scholarly.uftr.resolve_and_attach`` (UFTR v1.0).
    """
    candidates: list[str] = []
    url = (work.open_access_url or "").strip()
    if url:
        candidates.append(url)
    if work.pmcid:
        pmc_pdf = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{work.pmcid}/pdf/"
        if pmc_pdf not in candidates:
            candidates.append(pmc_pdf)
        epmc = f"https://europepmc.org/articles/{work.pmcid}?pdf=render"
        if epmc not in candidates:
            candidates.append(epmc)

    headers = {
        "User-Agent": f"Dhund/1.0 (Research OS; mailto:{_EMAIL})",
        "Accept": "application/pdf,*/*",
    }
    session = requests.Session()
    for candidate in candidates:
        try:
            resp = session.get(
                candidate,
                headers=headers,
                timeout=_TIMEOUT,
                allow_redirects=True,
                stream=True,
            )
            if resp.status_code >= 400:
                continue
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" in ctype and work.pmcid:
                epmc = f"https://europepmc.org/articles/{work.pmcid}?pdf=render"
                resp.close()
                if epmc == candidate:
                    continue
                resp = session.get(
                    epmc,
                    headers=headers,
                    timeout=_TIMEOUT,
                    allow_redirects=True,
                    stream=True,
                )
                ctype = (resp.headers.get("Content-Type") or "").lower()

            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    chunks = []
                    break
                chunks.append(chunk)
            resp.close()
            data = b"".join(chunks)
            if not data:
                continue
            if _looks_like_pdf(data, ctype):
                label = work.pmcid or (f"PMID{work.pmid}" if work.pmid else "europepmc")
                return data, f"{label}.pdf"
            if b"%PDF" not in data[:1024] and b"href" in data[:8000].lower():
                m = re.search(
                    br'href=["\']([^"\']+\.pdf[^"\']*)["\']',
                    data[:20000],
                    re.I,
                )
                if m:
                    next_url = urljoin(candidate, m.group(1).decode("utf-8", "ignore"))
                    if next_url not in candidates:
                        candidates.append(next_url)
        except Exception as exc:
            logger.debug("europe_pmc OA pdf download failed url=%s: %s", candidate, exc)
            continue
    return None
