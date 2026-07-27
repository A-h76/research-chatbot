"""Scholarly provider integrations — shared utilities.

Contracts:
- Soft-fail: public helpers return None on any error; callers continue.
- Short timeouts (default 5s).
- Circuit breaker: after N consecutive failures, skip live calls for a cool-down.
- Request coalescing: only one worker fetches a given cache_key at a time.
- Stale-while-revalidate: expired entries may still be returned while a
  background refresh runs.
- Metrics: every call records provider / endpoint / latency_ms / status /
  cache_hit into provider_metrics (best-effort; never raises).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        f"Soro/1.0 (Research OS; mailto:{os.environ.get('CROSSREF_MAILTO', 'admin@soro.app')})"
    ),
    "Accept": "application/json",
})

# ── Circuit breaker (in-process; enough for single-worker / 100-user scale) ───

_CIRCUIT_FAILURE_THRESHOLD = int(os.environ.get("PROVIDER_CIRCUIT_FAILURES", "5"))
_CIRCUIT_OPEN_SECONDS = int(os.environ.get("PROVIDER_CIRCUIT_OPEN_SECONDS", "300"))
_FETCH_LOCK_STALE_SECONDS = 30  # abandon a stuck "fetching" lock after this


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float | None = None


_circuits: dict[str, _CircuitState] = {}
_circuits_lock = threading.Lock()


def _circuit(provider: str) -> _CircuitState:
    with _circuits_lock:
        if provider not in _circuits:
            _circuits[provider] = _CircuitState()
        return _circuits[provider]


def circuit_is_open(provider: str) -> bool:
    state = _circuit(provider)
    if state.opened_at is None:
        return False
    if time.monotonic() - state.opened_at >= _CIRCUIT_OPEN_SECONDS:
        # Half-open: allow one probe.
        state.opened_at = None
        state.failures = 0
        return False
    return True


def circuit_record_success(provider: str) -> None:
    state = _circuit(provider)
    state.failures = 0
    state.opened_at = None


def circuit_record_failure(provider: str) -> None:
    state = _circuit(provider)
    state.failures += 1
    if state.failures >= _CIRCUIT_FAILURE_THRESHOLD:
        state.opened_at = time.monotonic()
        logger.warning(
            "circuit OPEN provider=%s after %s failures; skipping live calls for %ss",
            provider, state.failures, _CIRCUIT_OPEN_SECONDS,
        )


# ── Metrics ───────────────────────────────────────────────────────────────────

def record_metric(
    db: Any | None,
    *,
    provider: str,
    endpoint: str,
    latency_ms: int,
    status: str,
    cache_hit: bool = False,
) -> None:
    """Best-effort insert into provider_metrics. Never raises."""
    logger.info(
        "provider_metric provider=%s endpoint=%s latency_ms=%s status=%s cache_hit=%s",
        provider, endpoint, latency_ms, status, cache_hit,
    )
    if db is None:
        return
    try:
        from sqlalchemy import text as sa_text
        db.execute(
            sa_text(
                "INSERT INTO provider_metrics "
                "(provider, endpoint, latency_ms, status, cache_hit) "
                "VALUES (:p, :e, :l, :s, :c)"
            ),
            {"p": provider, "e": endpoint[:200], "l": int(latency_ms), "s": status[:30], "c": bool(cache_hit)},
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


# ── HTTP ──────────────────────────────────────────────────────────────────────

def provider_get(
    url: str,
    *,
    provider: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 5,
    retries: int = 0,
    db: Any | None = None,
) -> dict[str, Any] | None:
    """GET with timeout, circuit breaker, and metrics. Returns None on failure."""
    if circuit_is_open(provider):
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0, status="circuit_open")
        return None

    started = time.monotonic()
    last_status = "error"
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, headers=headers, timeout=timeout)
            latency = int((time.monotonic() - started) * 1000)
            if resp.status_code == 429:
                last_status = "rate_limited"
                circuit_record_failure(provider)
                record_metric(db, provider=provider, endpoint=endpoint, latency_ms=latency, status=last_status)
                return None
            if resp.status_code == 404:
                circuit_record_success(provider)
                record_metric(db, provider=provider, endpoint=endpoint, latency_ms=latency, status="ok")
                return None
            resp.raise_for_status()
            circuit_record_success(provider)
            record_metric(db, provider=provider, endpoint=endpoint, latency_ms=latency, status="ok")
            return resp.json()
        except requests.Timeout:
            last_status = "timeout"
            if attempt == retries:
                break
            time.sleep(0.3)
        except Exception as exc:
            last_status = "error"
            logger.warning("provider_get failed (%s %s): %s", provider, endpoint, exc)
            if attempt == retries:
                break
            time.sleep(0.3)

    latency = int((time.monotonic() - started) * 1000)
    circuit_record_failure(provider)
    record_metric(db, provider=provider, endpoint=endpoint, latency_ms=latency, status=last_status)
    return None


def cache_key_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:48]


# ── Cache ─────────────────────────────────────────────────────────────────────

@dataclass
class CacheEntry:
    data: dict[str, Any]
    is_fresh: bool
    is_stale: bool
    provider_version: str = ""


class ProviderCache:
    """DB-backed cache with stale-while-revalidate + fetch coalescing."""

    def __init__(self, db: Any, provider: str) -> None:
        self._db = db
        self._provider = provider

    def get(self, key: str, *, allow_stale: bool = False) -> CacheEntry | None:
        """Return a CacheEntry. Fresh hits always; stale only if allow_stale=True."""
        try:
            from sqlalchemy import text as sa_text
            row = self._db.execute(
                sa_text(
                    "SELECT response_json, expires_at, provider_version "
                    "FROM provider_cache WHERE provider=:p AND cache_key=:k LIMIT 1"
                ),
                {"p": self._provider, "k": key},
            ).fetchone()
            if row is None:
                return None
            expires_at = row[1]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            data = json.loads(row[0])
            version = (row[2] or "") if len(row) > 2 else ""
            if expires_at >= now:
                return CacheEntry(data=data, is_fresh=True, is_stale=False, provider_version=version)
            if allow_stale:
                return CacheEntry(data=data, is_fresh=False, is_stale=True, provider_version=version)
            return None
        except Exception:
            return None

    def set(
        self,
        key: str,
        data: dict[str, Any],
        ttl_hours: int = 24,
        *,
        provider_version: str = "",
    ) -> None:
        try:
            from sqlalchemy import text as sa_text
            expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
            self._db.execute(
                sa_text(
                    "INSERT INTO provider_cache "
                    "(provider, cache_key, response_json, expires_at, updated_at, "
                    " provider_version, fetch_status) "
                    "VALUES (:p, :k, :r, :e, NOW(), :v, 'ready') "
                    "ON CONFLICT (provider, cache_key) DO UPDATE "
                    "SET response_json=:r, expires_at=:e, updated_at=NOW(), "
                    "    provider_version=:v, fetch_status='ready', fetch_started_at=NULL"
                ),
                {
                    "p": self._provider,
                    "k": key,
                    "r": json.dumps(data, ensure_ascii=False),
                    "e": expires,
                    "v": provider_version or "",
                },
            )
            self._db.commit()
        except Exception as exc:
            logger.debug("ProviderCache.set failed silently: %s", exc)
            try:
                self._db.rollback()
            except Exception:
                pass

    def try_acquire_fetch_lock(self, key: str) -> bool:
        """Return True if this caller owns the fetch for `key`."""
        try:
            from sqlalchemy import text as sa_text
            # Clear stale locks first (portable — no INTERVAL syntax).
            stale_before = datetime.now(timezone.utc) - timedelta(seconds=_FETCH_LOCK_STALE_SECONDS)
            self._db.execute(
                sa_text(
                    "UPDATE provider_cache SET fetch_status='idle', fetch_started_at=NULL "
                    "WHERE provider=:p AND cache_key=:k AND fetch_status='fetching' "
                    "AND (fetch_started_at IS NULL OR fetch_started_at < :stale)"
                ),
                {"p": self._provider, "k": key, "stale": stale_before},
            )
            # Try insert-as-fetching; on conflict only win if currently idle/ready.
            result = self._db.execute(
                sa_text(
                    """
                    INSERT INTO provider_cache
                        (provider, cache_key, response_json, expires_at,
                         fetch_status, fetch_started_at, updated_at)
                    VALUES (:p, :k, '{}', :exp, 'fetching', :now, :now)
                    ON CONFLICT (provider, cache_key) DO UPDATE
                    SET fetch_status = 'fetching',
                        fetch_started_at = :now,
                        updated_at = :now
                    WHERE provider_cache.fetch_status IS DISTINCT FROM 'fetching'
                    RETURNING id
                    """
                ),
                {
                    "p": self._provider,
                    "k": key,
                    "exp": datetime.now(timezone.utc),
                    "now": datetime.now(timezone.utc),
                },
            )
            row = result.fetchone()
            self._db.commit()
            return row is not None
        except Exception:
            # SQLite / missing columns — fall through and allow fetch.
            try:
                self._db.rollback()
            except Exception:
                pass
            return True

    def release_fetch_lock(self, key: str) -> None:
        try:
            from sqlalchemy import text as sa_text
            self._db.execute(
                sa_text(
                    "UPDATE provider_cache SET fetch_status='idle', fetch_started_at=NULL "
                    "WHERE provider=:p AND cache_key=:k AND fetch_status='fetching'"
                ),
                {"p": self._provider, "k": key},
            )
            self._db.commit()
        except Exception:
            try:
                self._db.rollback()
            except Exception:
                pass


def get_or_fetch(
    cache: ProviderCache,
    key: str,
    fetch_fn: Callable[[], dict[str, Any] | None],
    *,
    ttl_hours: int,
    provider_version: str,
    endpoint: str,
    allow_stale: bool = True,
    background_refresh: bool = True,
) -> dict[str, Any] | None:
    """Cache lookup with coalescing + optional stale-while-revalidate.

    - Fresh hit → return immediately (metric: cache_hit).
    - Stale hit → return immediately; optionally refresh in a daemon thread.
    - Miss → acquire lock, fetch once, cache, return.
    - Contended miss → brief wait, then re-read cache.
    """
    provider = cache._provider
    db = cache._db

    entry = cache.get(key, allow_stale=allow_stale)
    if entry and entry.is_fresh:
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0,
                      status="cache_hit", cache_hit=True)
        return entry.data

    if entry and entry.is_stale:
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0,
                      status="cache_stale", cache_hit=True)
        if background_refresh and cache.try_acquire_fetch_lock(key):
            def _refresh() -> None:
                try:
                    data = fetch_fn()
                    if data is not None:
                        cache.set(key, data, ttl_hours, provider_version=provider_version)
                except Exception as exc:
                    logger.debug("background refresh failed %s/%s: %s", provider, key, exc)
                finally:
                    cache.release_fetch_lock(key)

            threading.Thread(target=_refresh, daemon=True, name=f"soro-refresh-{provider}").start()
        return entry.data

    # Cache miss — coalesce.
    if not cache.try_acquire_fetch_lock(key):
        time.sleep(0.4)
        again = cache.get(key, allow_stale=True)
        if again:
            record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0,
                          status="cache_hit", cache_hit=True)
            return again.data
        return None

    try:
        data = fetch_fn()
        if data is not None:
            cache.set(key, data, ttl_hours, provider_version=provider_version)
        return data
    finally:
        cache.release_fetch_lock(key)
