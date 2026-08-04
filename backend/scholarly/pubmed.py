"""PubMed (NCBI E-utilities) scholarly client.

Responsibility: biomedical discovery by keyword / PMID, with OA PDF hints
for Golden Rule import (Library → Analysis → Evidence).

Public API:
  search_works(query, page, per_page, db) → list[PubmedWork]
  get_work_by_pmid(pmid, db) → PubmedWork | None
  download_open_access_pdf(work, *, max_bytes) → tuple[bytes, str] | None

Env:
  ENABLE_PUBMED (default true)
  NCBI_API_KEY (optional — higher rate limits)
  CROSSREF_MAILTO / NCBI_EMAIL — tool identity (NCBI requirement)
  PUBMED_BASE_URL / EUROPEPMC_BASE_URL — overrides for tests
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

from backend.scholarly import ProviderCache, get_or_fetch, provider_get

logger = logging.getLogger(__name__)

_EUTILS = os.environ.get(
    "PUBMED_BASE_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
).rstrip("/")
_EUROPEPMC = os.environ.get(
    "EUROPEPMC_BASE_URL", "https://www.ebi.ac.uk/europepmc/webservices/rest"
).rstrip("/")
_TIMEOUT = int(os.environ.get("PUBMED_TIMEOUT", "8"))
_EMAIL = (
    os.environ.get("NCBI_EMAIL")
    or os.environ.get("CROSSREF_MAILTO")
    or "admin@dhund.com"
)
_TOOL = os.environ.get("NCBI_TOOL", "dhund")
_API_KEY = (os.environ.get("NCBI_API_KEY") or "").strip()
_VERSION = "v1"

_PMID_RE = re.compile(r"^\d{1,12}$")
_PMCID_RE = re.compile(r"^(?:PMC)?(\d+)$", re.I)


@dataclass
class PubmedWork:
    id: str = ""  # pmid string — Discover card key
    pmid: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    citation_count: int = 0
    open_access_url: str = ""
    pmcid: str = ""
    concepts: list[str] = field(default_factory=list)
    source: str = "pubmed"
    is_open_access: bool = False


def _ncbi_params(**extra: Any) -> dict[str, Any]:
    p: dict[str, Any] = {
        "tool": _TOOL,
        "email": _EMAIL,
        "retmode": "json",
    }
    if _API_KEY:
        p["api_key"] = _API_KEY
    p.update(extra)
    return p


def normalize_pmid(value: str | int | None) -> str:
    raw = str(value or "").strip()
    raw = re.sub(r"(?i)^pmid[:\s]*", "", raw).strip()
    if not _PMID_RE.match(raw):
        return ""
    return str(int(raw))  # drop leading zeros


def normalize_pmcid(value: str | None) -> str:
    raw = (value or "").strip()
    m = _PMCID_RE.match(raw)
    if not m:
        return ""
    return f"PMC{m.group(1)}"


def _year_from_pubdate(pubdate: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", pubdate or "")
    return int(m.group(0)) if m else None


def _authors_from_esummary(item: dict[str, Any]) -> str:
    authors = item.get("authors") or []
    names: list[str] = []
    for a in authors[:12]:
        name = (a.get("name") or "").strip()
        if name:
            names.append(name)
    return "; ".join(names)


def _ids_from_articleids(item: dict[str, Any]) -> tuple[str, str]:
    doi = ""
    pmcid = ""
    for aid in item.get("articleids") or []:
        idtype = (aid.get("idtype") or "").lower()
        val = (aid.get("value") or "").strip()
        if idtype == "doi" and val:
            doi = val.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        elif idtype in ("pmc", "pmcid") and val:
            pmcid = normalize_pmcid(val)
    return doi, pmcid


def _parse_esummary_item(uid: str, item: dict[str, Any]) -> PubmedWork:
    pmid = normalize_pmid(uid) or normalize_pmid(item.get("uid"))
    doi, pmcid = _ids_from_articleids(item)
    title = (item.get("title") or "").strip()
    venue = (item.get("fulljournalname") or item.get("source") or "").strip()
    year = _year_from_pubdate(str(item.get("pubdate") or ""))
    oa_url = ""
    if pmcid:
        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    return PubmedWork(
        id=pmid,
        pmid=pmid,
        doi=doi,
        title=title,
        authors=_authors_from_esummary(item),
        year=year,
        venue=venue,
        abstract="",
        open_access_url=oa_url,
        pmcid=pmcid,
        is_open_access=bool(pmcid),
        source="pubmed",
    )


def _enrich_from_europepmc(work: PubmedWork, *, db: Any) -> PubmedWork:
    """Fill abstract / OA URL / PMCID via Europe PMC (OA resolver for PubMed)."""
    pmid = work.pmid
    if not pmid:
        return work

    cache = ProviderCache(db, "pubmed")
    cache_key = f"epmc:{pmid}"

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_EUROPEPMC}/search",
            provider="pubmed",
            endpoint="europepmc/search",
            params={
                "query": f"EXT_ID:{pmid} AND SRC:MED",
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
        endpoint="europepmc/search",
        allow_stale=True,
        background_refresh=True,
    )
    if not hit or hit.get("empty"):
        return work

    abstract = (hit.get("abstractText") or "").strip()
    if abstract and not work.abstract:
        work.abstract = abstract[:4000]

    doi = (hit.get("doi") or "").strip()
    if doi and not work.doi:
        work.doi = doi.removeprefix("https://doi.org/")

    pmcid = normalize_pmcid(hit.get("pmcid") or "")
    if pmcid:
        work.pmcid = pmcid

    is_oa = str(hit.get("isOpenAccess") or "").lower() in ("y", "yes", "true", "1")
    work.is_open_access = work.is_open_access or is_oa

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

    if not pdf_url and work.pmcid and (is_oa or work.is_open_access):
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{work.pmcid}/pdf/"

    if pdf_url:
        work.open_access_url = pdf_url
        work.is_open_access = True

    mesh = []
    for m in hit.get("meshHeadingList", {}).get("meshHeading") or []:
        label = (m.get("descriptorName") or "").strip()
        if label:
            mesh.append(label)
    if mesh and not work.concepts:
        work.concepts = mesh[:8]

    return work


def _esummary_works(pmids: list[str], *, db: Any) -> list[PubmedWork]:
    if not pmids:
        return []
    ids = ",".join(pmids)
    cache = ProviderCache(db, "pubmed")
    cache_key = hashlib.sha256(f"esummary:{ids}".encode()).hexdigest()[:48]

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_EUTILS}/esummary.fcgi",
            provider="pubmed",
            endpoint="esummary",
            params=_ncbi_params(db="pubmed", id=ids),
            timeout=_TIMEOUT,
            db=db,
        )
        if not raw:
            return None
        return raw

    raw = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=6,
        provider_version=_VERSION,
        endpoint="esummary",
        allow_stale=True,
        background_refresh=True,
    )
    if not raw:
        return []

    result = raw.get("result") or {}
    works: list[PubmedWork] = []
    for uid in pmids:
        item = result.get(uid) or result.get(str(uid))
        if not item or not isinstance(item, dict):
            continue
        if item.get("error"):
            continue
        works.append(_parse_esummary_item(uid, item))
    return works


def search_works(
    query: str,
    *,
    page: int = 1,
    per_page: int = 15,
    db: Any,
    enrich: bool = True,
) -> list[PubmedWork]:
    """Search PubMed. Cached; optional Europe PMC enrich for abstract/OA."""
    query = (query or "").strip()
    if not query:
        return []

    page = max(1, int(page))
    per_page = min(20, max(1, int(per_page)))
    retstart = (page - 1) * per_page

    # Bare PMID → direct lookup
    cleaned = re.sub(r"(?i)^pmid[:\s]*", "", query).strip()
    pmid_only = normalize_pmid(cleaned)
    if pmid_only and _PMID_RE.match(cleaned):
        work = get_work_by_pmid(pmid_only, db=db, enrich=enrich)
        return [work] if work else []

    cache = ProviderCache(db, "pubmed")
    cache_key = hashlib.sha256(
        f"esearch:{query.lower()}:{page}:{per_page}".encode()
    ).hexdigest()[:48]

    def _fetch() -> dict[str, Any] | None:
        raw = provider_get(
            f"{_EUTILS}/esearch.fcgi",
            provider="pubmed",
            endpoint="esearch",
            params=_ncbi_params(
                db="pubmed",
                term=query,
                retmax=per_page,
                retstart=retstart,
                sort="relevance",
            ),
            timeout=_TIMEOUT,
            db=db,
        )
        if not raw:
            return None
        return raw

    raw = get_or_fetch(
        cache,
        cache_key,
        _fetch,
        ttl_hours=1,
        provider_version=_VERSION,
        endpoint="esearch",
        allow_stale=True,
        background_refresh=True,
    )
    if not raw:
        return []

    idlist = ((raw.get("esearchresult") or {}).get("idlist")) or []
    pmids = [normalize_pmid(x) for x in idlist if normalize_pmid(x)]
    works = _esummary_works(pmids, db=db)
    if enrich:
        works = [_enrich_from_europepmc(w, db=db) for w in works]
    return works


def get_work_by_pmid(
    pmid: str,
    *,
    db: Any,
    enrich: bool = True,
) -> PubmedWork | None:
    pmid = normalize_pmid(pmid)
    if not pmid:
        return None
    works = _esummary_works([pmid], db=db)
    if not works:
        return None
    work = works[0]
    if enrich:
        work = _enrich_from_europepmc(work, db=db)
    return work


def _looks_like_pdf(data: bytes, content_type: str) -> bool:
    if data[:4] == b"%PDF":
        return True
    ct = (content_type or "").lower()
    return "pdf" in ct and data[:4] == b"%PDF"


def download_open_access_pdf(
    work: PubmedWork,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str] | None:
    """Legacy/internal OA download — not the acquisition API.

    New library/Discover code must use ``backend.scholarly.uftr.resolve_and_attach``
    (UFTR v1.0). This helper remains for scholarly tests / internal use only.
    """
    candidates: list[str] = []
    url = (work.open_access_url or "").strip()
    if url:
        candidates.append(url)
    if work.pmcid:
        pmc_pdf = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{work.pmcid}/pdf/"
        if pmc_pdf not in candidates:
            candidates.append(pmc_pdf)

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
            # Some PMC links return HTML interstitial — follow pdf link if present
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" in ctype and work.pmcid:
                # try europepmc pdf mirror
                epmc = (
                    f"https://europepmc.org/articles/{work.pmcid}"
                    f"?pdf=render"
                )
                resp.close()
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
                fname = f"PMID{work.pmid or 'unknown'}.pdf"
                return data, fname
            # Absolute PDF URL sometimes behind HTML — try urljoin of first pdf href
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
            logger.debug("pubmed OA pdf download failed url=%s: %s", candidate, exc)
            continue
    return None
