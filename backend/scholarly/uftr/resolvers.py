"""UFTR candidate discovery — Resolver ≠ Validator.

Resolvers only emit candidate URLs + provisional signals.
The Validator decides FOUND vs failure outcomes.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_ARXIV_IN_DOI = re.compile(r"^10\.48550/arXiv\.(.+)$", re.I)


@dataclass(frozen=True)
class Candidate:
    """One URL to try, tagged by which resolver produced it."""

    url: str
    resolver: str  # provider | openalex | unpaywall | europe_pmc | arxiv | source_url
    hint: str = ""


def normalize_doi(doi: str) -> str:
    raw = (doi or "").strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.I)
    return raw.strip()


def _looks_like_url(url: str) -> bool:
    u = (url or "").strip()
    if not u or len(u) > 2000:
        return False
    try:
        p = urlparse(u)
    except Exception:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


def _dedupe_append(out: list[Candidate], seen: set[str], cand: Candidate) -> None:
    url = (cand.url or "").strip()
    if not _looks_like_url(url):
        return
    key = url.lower().rstrip("/")
    if key in seen:
        return
    seen.add(key)
    out.append(Candidate(url=url, resolver=cand.resolver, hint=cand.hint))


def _arxiv_id_from_doi(doi: str) -> str:
    m = _ARXIV_IN_DOI.match(normalize_doi(doi))
    return (m.group(1) or "").strip() if m else ""


def collect_candidates(
    *,
    doi: str = "",
    open_access_url: str = "",
    source_url: str = "",
    pmcid: str = "",
    arxiv_id: str = "",
    provider: str = "",
    db: Any = None,
) -> list[Candidate]:
    """Ordered candidate list per Product Hardening #1.

    1. Provider-native OA URL (and source_url fallback)
    2. OpenAlex OA location (DOI)
    3. Unpaywall url_for_pdf
    4. Europe PMC / PMC
    5. arXiv
    """
    out: list[Candidate] = []
    seen: set[str] = set()
    doi_n = normalize_doi(doi)
    provider = (provider or "").strip().lower()
    pmcid = (pmcid or "").strip()
    if pmcid and not pmcid.upper().startswith("PMC"):
        pmcid = f"PMC{pmcid}" if pmcid.isdigit() else pmcid
    arxiv_id = (arxiv_id or "").strip()
    if not arxiv_id and doi_n:
        arxiv_id = _arxiv_id_from_doi(doi_n)

    # 1. Provider / known OA URL first (often the best shot)
    for url, resolver in (
        (open_access_url, "provider"),
        (source_url, "source_url"),
    ):
        _dedupe_append(out, seen, Candidate(url=url, resolver=resolver, hint=provider or ""))

    # 2. OpenAlex best OA (needs db for ProviderCache; soft-skip without it)
    if doi_n and _DOI_RE.match(doi_n) and db is not None:
        try:
            from backend.scholarly.openalex import get_work_by_doi

            work = get_work_by_doi(doi_n, db=db)
            if work and getattr(work, "open_access_url", None):
                _dedupe_append(
                    out,
                    seen,
                    Candidate(url=work.open_access_url, resolver="openalex", hint="best_oa"),
                )
        except Exception as exc:
            logger.debug("uftr openalex resolver soft-fail doi=%s: %s", doi_n[:40], exc)

    # 3. Unpaywall
    if doi_n and _DOI_RE.match(doi_n):
        try:
            from backend.scholarly.unpaywall import lookup_oa_pdf_url

            url = lookup_oa_pdf_url(doi_n, db=db)
            if url:
                _dedupe_append(
                    out,
                    seen,
                    Candidate(url=url, resolver="unpaywall", hint="url_for_pdf"),
                )
        except Exception as exc:
            logger.debug("uftr unpaywall resolver soft-fail doi=%s: %s", doi_n[:40], exc)

    # 4. Europe PMC / PMC
    if pmcid:
        _dedupe_append(
            out,
            seen,
            Candidate(
                url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
                resolver="europe_pmc",
                hint="pmc_pdf",
            ),
        )
        _dedupe_append(
            out,
            seen,
            Candidate(
                url=f"https://europepmc.org/articles/{pmcid}?pdf=render",
                resolver="europe_pmc",
                hint="epmc_render",
            ),
        )

    # 5. arXiv
    if arxiv_id or provider == "arxiv":
        try:
            from backend.scholarly.arxiv import pdf_url_for, normalize_arxiv_id

            aid = normalize_arxiv_id(arxiv_id) or arxiv_id
            if aid:
                _dedupe_append(
                    out,
                    seen,
                    Candidate(url=pdf_url_for(aid), resolver="arxiv", hint=aid),
                )
        except Exception as exc:
            logger.debug("uftr arxiv resolver soft-fail: %s", exc)

    return out


def hints_from_user_file(uf: Any) -> dict[str, str]:
    """Extract resolver inputs from a UserFile / stub row."""
    doi = (getattr(uf, "doi", None) or "").strip()
    source_url = (getattr(uf, "source_url", None) or "").strip()
    provider = (getattr(uf, "external_provider", None) or getattr(uf, "metadata_source", None) or "").strip()
    # tags may carry pmcid / arxiv for discover stubs
    pmcid = ""
    arxiv_id = ""
    tags_raw = getattr(uf, "tags", None) or "[]"
    try:
        import json

        tags = json.loads(tags_raw) if isinstance(tags_raw, str) else (tags_raw or [])
        if isinstance(tags, list):
            for t in tags:
                s = str(t)
                if s.upper().startswith("PMC") or s.lower().startswith("pmcid:"):
                    pmcid = s.split(":", 1)[-1].strip() if ":" in s else s
                if s.lower().startswith("arxiv:"):
                    arxiv_id = s.split(":", 1)[-1].strip()
                if s.lower().startswith("pmid:"):
                    pass
    except Exception:
        pass

    # external_item_id patterns
    ext = (getattr(uf, "external_item_id", None) or "").strip()
    if ext.upper().startswith("PMC"):
        pmcid = pmcid or ext
    if not arxiv_id and provider == "arxiv":
        arxiv_id = ext

    return {
        "doi": doi,
        "open_access_url": source_url,  # Discover stores OA URL here
        "source_url": source_url,
        "pmcid": pmcid,
        "arxiv_id": arxiv_id,
        "provider": provider,
    }
