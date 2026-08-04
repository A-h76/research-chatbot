"""Unpaywall DOI → OA PDF URL (soft-fail)."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any

from backend.scholarly import ProviderCache, get_or_fetch, provider_get

logger = logging.getLogger(__name__)

_BASE = os.environ.get("UNPAYWALL_BASE_URL", "https://api.unpaywall.org/v2").rstrip("/")
_EMAIL = (
    os.environ.get("UNPAYWALL_EMAIL")
    or os.environ.get("CROSSREF_MAILTO")
    or "admin@dhund.com"
)
_VERSION = "v2"
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def normalize_doi(doi: str) -> str:
    raw = (doi or "").strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.I)
    return raw.strip()


def unpaywall_enabled() -> bool:
    return os.environ.get("ENABLE_UNPAYWALL", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def lookup_oa_pdf_url(doi: str, *, db: Any = None) -> str:
    """Return best Unpaywall pdf URL or ''."""
    if not unpaywall_enabled():
        return ""
    doi = normalize_doi(doi)
    if not doi or not _DOI_RE.match(doi):
        return ""

    def _parse(data: dict[str, Any] | None) -> str:
        if not isinstance(data, dict):
            return ""
        best = data.get("best_oa_location") or {}
        if isinstance(best, dict):
            url = (best.get("url_for_pdf") or best.get("url") or "").strip()
            if url:
                return url
        for loc in data.get("oa_locations") or []:
            if not isinstance(loc, dict):
                continue
            url = (loc.get("url_for_pdf") or "").strip()
            if url:
                return url
        return ""

    if db is None:
        raw = provider_get(
            f"{_BASE}/{doi}",
            provider="unpaywall",
            endpoint="doi",
            params={"email": _EMAIL},
            timeout=8,
            db=None,
        )
        return _parse(raw)

    cache = ProviderCache(db, "unpaywall")
    key = hashlib.sha256(f"doi:{doi.lower()}".encode()).hexdigest()[:48]

    def _fetch() -> dict[str, Any] | None:
        return provider_get(
            f"{_BASE}/{doi}",
            provider="unpaywall",
            endpoint="doi",
            params={"email": _EMAIL},
            timeout=8,
            db=db,
        )

    raw = get_or_fetch(
        cache,
        key,
        _fetch,
        ttl_hours=24,
        provider_version=_VERSION,
        endpoint="doi",
        allow_stale=True,
        background_refresh=True,
    )
    return _parse(raw)
