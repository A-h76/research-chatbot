"""UFTR resolver-result caching via ProviderCache pattern.

Caches resolution *metadata* (not PDF bytes) keyed by DOI or provider id.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from backend.scholarly import ProviderCache, get_or_fetch
from backend.scholarly.uftr.outcomes import FullTextOutcome

logger = logging.getLogger(__name__)

_PROVIDER = "uftr"
_VERSION = "v1"

# TTL hours by outcome class (Product Hardening #1)
TTL_FOUND_HOURS = 24 * 30  # 30d — successful URL+source
TTL_NO_OA_HOURS = 24
TTL_BLOCKED_HOURS = 48  # paywall / bot — medium-short
TTL_TRANSIENT_HOURS = 6  # network / timeout / invalid — retry sooner


def cache_key(*, doi: str = "", provider_id: str = "") -> str:
    doi = (doi or "").strip().lower()
    if doi:
        raw = f"doi:{doi}"
    else:
        pid = (provider_id or "").strip().lower()
        raw = f"id:{pid}" if pid else ""
    if not raw:
        return ""
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def ttl_for_outcome(outcome: FullTextOutcome | str) -> int:
    val = outcome.value if isinstance(outcome, FullTextOutcome) else str(outcome)
    if val == FullTextOutcome.FOUND.value:
        return TTL_FOUND_HOURS
    if val == FullTextOutcome.NO_OPEN_ACCESS.value:
        return TTL_NO_OA_HOURS
    if val in (
        FullTextOutcome.PUBLISHER_PAYWALL.value,
        FullTextOutcome.BOT_PROTECTION.value,
    ):
        return TTL_BLOCKED_HOURS
    return TTL_TRANSIENT_HOURS


def get_cached_resolution(db: Any, *, doi: str = "", provider_id: str = "") -> dict[str, Any] | None:
    """Return cached public resolution dict or None. Soft-fails."""
    if db is None:
        return None
    key = cache_key(doi=doi, provider_id=provider_id)
    if not key:
        return None
    try:
        cache = ProviderCache(db, _PROVIDER)
        entry = cache.get(key, allow_stale=True)
        if entry and isinstance(entry.data, dict):
            return entry.data
    except Exception as exc:
        logger.debug("uftr cache get soft-fail: %s", exc)
    return None


def store_resolution(
    db: Any,
    *,
    doi: str = "",
    provider_id: str = "",
    payload: dict[str, Any],
    outcome: FullTextOutcome | str,
) -> None:
    """Persist resolution metadata. Soft-fails; never raises."""
    if db is None or not isinstance(payload, dict):
        return
    key = cache_key(doi=doi, provider_id=provider_id)
    if not key:
        return
    try:
        cache = ProviderCache(db, _PROVIDER)
        ttl = ttl_for_outcome(outcome)
        # Store without bytes
        clean = {k: v for k, v in payload.items() if k != "data"}
        cache.set(key, clean, ttl, provider_version=_VERSION)
    except Exception as exc:
        logger.debug("uftr cache set soft-fail: %s", exc)


def get_or_resolve_cached(
    db: Any,
    *,
    doi: str,
    provider_id: str,
    resolve_fn,
) -> dict[str, Any] | None:
    """Optional coalesced path for metadata-only re-imports.

    Note: live PDF download is still done by resolve_full_text; this caches
    the *outcome* so retries within TTL can short-circuit discovery when
    we already know NO_OPEN_ACCESS / paywall / bot (skip hammering APIs).
    """
    key = cache_key(doi=doi, provider_id=provider_id)
    if not key or db is None:
        return resolve_fn()

    cache = ProviderCache(db, _PROVIDER)

    def _fetch() -> dict[str, Any] | None:
        return resolve_fn()

    try:
        return get_or_fetch(
            cache,
            key,
            _fetch,
            ttl_hours=TTL_NO_OA_HOURS,
            provider_version=_VERSION,
            endpoint="resolve",
            allow_stale=True,
            background_refresh=False,
        )
    except Exception:
        return resolve_fn()
