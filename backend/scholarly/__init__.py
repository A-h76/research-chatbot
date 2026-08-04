"""Scholarly provider integrations — shared utilities.

Contracts:
- Soft-fail: public helpers return None on any error; callers continue.
- Short timeouts (default 5s).
- Feature flags: ENABLE_CROSSREF / ENABLE_OPENALEX / ENABLE_SEMANTIC_SCHOLAR /
  ENABLE_PUBMED / ENABLE_ARXIV / ENABLE_EUROPE_PMC / ENABLE_ORCID /
  ENABLE_UNPAYWALL / ENABLE_UFTR.
- Bulkhead: per-provider concurrency caps so one stalled provider cannot
  monopolise worker threads.
- Circuit breaker: DB-backed (shared across Gunicorn + worker processes).
- Request coalescing: DB-backed fetch locks on provider_cache (not in-process).
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
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        f"Dhund/1.0 (Research OS; mailto:{os.environ.get('CROSSREF_MAILTO', 'admin@dhund.com')})"
    ),
    "Accept": "application/json",
})

# Stable identity for this process — written into fetch locks for ops visibility.
_PROCESS_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"

_CIRCUIT_FAILURE_THRESHOLD = int(os.environ.get("PROVIDER_CIRCUIT_FAILURES", "5"))
_CIRCUIT_OPEN_SECONDS = int(os.environ.get("PROVIDER_CIRCUIT_OPEN_SECONDS", "300"))
_FETCH_LOCK_STALE_SECONDS = 30
_BULKHEAD_WAIT_SECONDS = float(os.environ.get("PROVIDER_BULKHEAD_WAIT", "0.15"))

_FLAG_ENV = {
    "crossref": "ENABLE_CROSSREF",
    "openalex": "ENABLE_OPENALEX",
    "semantic_scholar": "ENABLE_SEMANTIC_SCHOLAR",
    "pubmed": "ENABLE_PUBMED",
    "arxiv": "ENABLE_ARXIV",
    "europe_pmc": "ENABLE_EUROPE_PMC",
    "orcid": "ENABLE_ORCID",
    "unpaywall": "ENABLE_UNPAYWALL",
    "uftr": "ENABLE_UFTR",
}

_BULKHEAD_LIMITS = {
    "crossref": int(os.environ.get("PROVIDER_BULKHEAD_CROSSREF", "2")),
    "openalex": int(os.environ.get("PROVIDER_BULKHEAD_OPENALEX", "2")),
    "semantic_scholar": int(os.environ.get("PROVIDER_BULKHEAD_SEMANTIC_SCHOLAR", "2")),
    "pubmed": int(os.environ.get("PROVIDER_BULKHEAD_PUBMED", "2")),
    "arxiv": int(os.environ.get("PROVIDER_BULKHEAD_ARXIV", "2")),
    "europe_pmc": int(os.environ.get("PROVIDER_BULKHEAD_EUROPE_PMC", "2")),
    "orcid": int(os.environ.get("PROVIDER_BULKHEAD_ORCID", "2")),
}

_bulkheads: dict[str, threading.BoundedSemaphore] = {
    name: threading.BoundedSemaphore(max(1, limit))
    for name, limit in _BULKHEAD_LIMITS.items()
}
_bulkhead_inflight: dict[str, int] = {name: 0 for name in _BULKHEAD_LIMITS}
_bulkhead_inflight_lock = threading.Lock()


# ── Feature flags ─────────────────────────────────────────────────────────────

def _env_truthy(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def provider_enabled(provider: str) -> bool:
    env_name = _FLAG_ENV.get(provider)
    if not env_name:
        return True
    return _env_truthy(env_name, "true")


# ── Bulkhead ──────────────────────────────────────────────────────────────────

def _bulkhead_acquire(provider: str) -> bool:
    sem = _bulkheads.get(provider)
    if sem is None:
        return True
    ok = sem.acquire(timeout=_BULKHEAD_WAIT_SECONDS)
    if ok:
        with _bulkhead_inflight_lock:
            _bulkhead_inflight[provider] = _bulkhead_inflight.get(provider, 0) + 1
    return ok


def _bulkhead_release(provider: str) -> None:
    sem = _bulkheads.get(provider)
    if sem is None:
        return
    try:
        sem.release()
    except ValueError:
        pass
    with _bulkhead_inflight_lock:
        _bulkhead_inflight[provider] = max(0, _bulkhead_inflight.get(provider, 0) - 1)


def bulkhead_stats() -> dict[str, dict[str, int]]:
    with _bulkhead_inflight_lock:
        return {
            name: {
                "limit": _BULKHEAD_LIMITS.get(name, 0),
                "inflight": _bulkhead_inflight.get(name, 0),
            }
            for name in _BULKHEAD_LIMITS
        }


# ── Circuit breaker (DB-backed) ───────────────────────────────────────────────

def _ensure_circuit_row(db: Any, provider: str) -> None:
    from sqlalchemy import text as sa_text
    db.execute(
        sa_text(
            "INSERT INTO provider_circuit (provider, failures, opened_at, updated_at) "
            "VALUES (:p, 0, NULL, NOW()) "
            "ON CONFLICT (provider) DO NOTHING"
        ),
        {"p": provider},
    )


def circuit_is_open(provider: str, db: Any | None = None) -> bool:
    """True when the provider circuit is open (shared across all processes)."""
    if db is None:
        return False
    try:
        from sqlalchemy import text as sa_text
        _ensure_circuit_row(db, provider)
        row = db.execute(
            sa_text(
                "SELECT failures, opened_at FROM provider_circuit WHERE provider=:p LIMIT 1"
            ),
            {"p": provider},
        ).fetchone()
        db.commit()
        if row is None or row[1] is None:
            return False
        opened_at = row[1]
        if isinstance(opened_at, str):
            opened_at = datetime.fromisoformat(opened_at)
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - opened_at).total_seconds()
        if age >= _CIRCUIT_OPEN_SECONDS:
            # Half-open: clear so one probe can run.
            db.execute(
                sa_text(
                    "UPDATE provider_circuit SET failures=0, opened_at=NULL, updated_at=NOW() "
                    "WHERE provider=:p"
                ),
                {"p": provider},
            )
            db.commit()
            return False
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False


def circuit_record_success(provider: str, db: Any | None = None) -> None:
    if db is None:
        return
    try:
        from sqlalchemy import text as sa_text
        db.execute(
            sa_text(
                "UPDATE provider_circuit SET failures=0, opened_at=NULL, updated_at=NOW() "
                "WHERE provider=:p"
            ),
            {"p": provider},
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def circuit_record_failure(provider: str, db: Any | None = None) -> None:
    if db is None:
        return
    try:
        from sqlalchemy import text as sa_text
        _ensure_circuit_row(db, provider)
        db.execute(
            sa_text(
                "UPDATE provider_circuit SET failures = failures + 1, updated_at = NOW() "
                "WHERE provider=:p"
            ),
            {"p": provider},
        )
        row = db.execute(
            sa_text("SELECT failures FROM provider_circuit WHERE provider=:p"),
            {"p": provider},
        ).fetchone()
        failures = int(row[0]) if row else 0
        if failures >= _CIRCUIT_FAILURE_THRESHOLD:
            db.execute(
                sa_text(
                    "UPDATE provider_circuit SET opened_at=COALESCE(opened_at, NOW()), "
                    "updated_at=NOW() WHERE provider=:p"
                ),
                {"p": provider},
            )
            logger.warning(
                "circuit OPEN provider=%s after %s failures; skipping live calls for %ss",
                provider, failures, _CIRCUIT_OPEN_SECONDS,
            )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def circuit_status(provider: str, db: Any) -> str:
    """healthy | circuit_open | disabled"""
    if not provider_enabled(provider):
        return "disabled"
    if circuit_is_open(provider, db):
        return "circuit_open"
    return "healthy"


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


def cache_hit_rate(db: Any, *, hours: int = 24) -> float | None:
    """Fraction of metric rows that were cache hits over the last N hours."""
    try:
        from sqlalchemy import text as sa_text
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        row = db.execute(
            sa_text(
                "SELECT "
                "COUNT(*) FILTER (WHERE cache_hit = TRUE)::float / NULLIF(COUNT(*), 0) "
                "FROM provider_metrics WHERE created_at >= :since"
            ),
            {"since": since},
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return round(float(row[0]), 4)
    except Exception:
        # SQLite fallback without FILTER
        try:
            from sqlalchemy import text as sa_text
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            row = db.execute(
                sa_text(
                    "SELECT "
                    "SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) * 1.0 / "
                    "NULLIF(COUNT(*), 0) "
                    "FROM provider_metrics WHERE created_at >= :since"
                ),
                {"since": since},
            ).fetchone()
            if row is None or row[0] is None:
                return None
            return round(float(row[0]), 4)
        except Exception:
            return None


def providers_health(db: Any) -> dict[str, Any]:
    """Payload for GET /api/health/providers."""
    providers = (
        "crossref",
        "openalex",
        "semantic_scholar",
        "pubmed",
        "arxiv",
        "europe_pmc",
        "orcid",
    )
    status = {p: circuit_status(p, db) for p in providers}
    hit = cache_hit_rate(db)
    return {
        **status,
        "cache_hit_rate": hit if hit is not None else 0.0,
        "bulkheads": bulkhead_stats(),
        "process_id": _PROCESS_ID,
    }


# ── Cleanup ───────────────────────────────────────────────────────────────────

def cleanup_provider_tables(
    db: Any,
    *,
    metrics_keep_days: int = 14,
) -> dict[str, int]:
    """Delete expired cache rows and old metrics. Safe to run daily."""
    from sqlalchemy import text as sa_text
    now = datetime.now(timezone.utc)
    metrics_before = now - timedelta(days=metrics_keep_days)

    cache_deleted = db.execute(
        sa_text(
            "DELETE FROM provider_cache WHERE expires_at < :now "
            "AND (fetch_status IS NULL OR fetch_status <> 'fetching')"
        ),
        {"now": now},
    ).rowcount or 0

    metrics_deleted = db.execute(
        sa_text("DELETE FROM provider_metrics WHERE created_at < :before"),
        {"before": metrics_before},
    ).rowcount or 0

    # Release abandoned fetch locks.
    stale_before = now - timedelta(seconds=_FETCH_LOCK_STALE_SECONDS)
    locks_cleared = db.execute(
        sa_text(
            "UPDATE provider_cache SET fetch_status='idle', fetch_started_at=NULL, "
            "locked_by=NULL WHERE fetch_status='fetching' "
            "AND (fetch_started_at IS NULL OR fetch_started_at < :stale)"
        ),
        {"stale": stale_before},
    ).rowcount or 0

    db.commit()
    return {
        "cache_deleted": int(cache_deleted),
        "metrics_deleted": int(metrics_deleted),
        "locks_cleared": int(locks_cleared),
    }


def try_daily_cleanup(db: Any) -> dict[str, int] | None:
    """Run cleanup at most once per day across all processes (DB lock)."""
    cache = ProviderCache(db, "_system")
    existing = cache.get("cleanup:daily")
    if existing and existing.is_fresh:
        return None
    if not cache.try_acquire_fetch_lock("cleanup:daily"):
        return None
    try:
        again = cache.get("cleanup:daily")
        if again and again.is_fresh:
            return None
        result = cleanup_provider_tables(db)
        cache.set(
            "cleanup:daily",
            {"last_run": datetime.now(timezone.utc).isoformat(), **result},
            ttl_hours=24,
            provider_version="ops",
        )
        logger.info("provider cleanup done: %s", result)
        return result
    finally:
        cache.release_fetch_lock("cleanup:daily")


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
    """GET with flags, bulkhead, circuit breaker, and metrics. Soft-fails to None."""
    if not provider_enabled(provider):
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0, status="disabled")
        return None

    if circuit_is_open(provider, db):
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0, status="circuit_open")
        return None

    if not _bulkhead_acquire(provider):
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0, status="bulkhead_full")
        return None

    started = time.monotonic()
    last_status = "error"
    try:
        for attempt in range(retries + 1):
            try:
                resp = _SESSION.get(url, params=params, headers=headers, timeout=timeout)
                latency = int((time.monotonic() - started) * 1000)
                if resp.status_code == 429:
                    last_status = "rate_limited"
                    circuit_record_failure(provider, db)
                    record_metric(db, provider=provider, endpoint=endpoint,
                                  latency_ms=latency, status=last_status)
                    return None
                if resp.status_code == 404:
                    circuit_record_success(provider, db)
                    record_metric(db, provider=provider, endpoint=endpoint,
                                  latency_ms=latency, status="ok")
                    return None
                resp.raise_for_status()
                circuit_record_success(provider, db)
                record_metric(db, provider=provider, endpoint=endpoint,
                              latency_ms=latency, status="ok")
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
        circuit_record_failure(provider, db)
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=latency, status=last_status)
        return None
    finally:
        _bulkhead_release(provider)


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
    """DB-backed cache with stale-while-revalidate + distributed fetch locks.

    Locks live in provider_cache (fetch_status / fetch_started_at / locked_by)
    so Gunicorn and worker processes share the same coalescing state.
    """

    def __init__(self, db: Any, provider: str) -> None:
        self._db = db
        self._provider = provider

    def get(self, key: str, *, allow_stale: bool = False) -> CacheEntry | None:
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
            now = datetime.now(timezone.utc)
            expires = now + timedelta(hours=ttl_hours)
            self._db.execute(
                sa_text(
                    "INSERT INTO provider_cache "
                    "(provider, cache_key, response_json, expires_at, updated_at, "
                    " provider_version, fetch_status, locked_by) "
                    "VALUES (:p, :k, :r, :e, :now, :v, 'ready', NULL) "
                    "ON CONFLICT (provider, cache_key) DO UPDATE "
                    "SET response_json=:r, expires_at=:e, updated_at=:now, "
                    "    provider_version=:v, fetch_status='ready', "
                    "    fetch_started_at=NULL, locked_by=NULL"
                ),
                {
                    "p": self._provider,
                    "k": key,
                    "r": json.dumps(data, ensure_ascii=False),
                    "e": expires,
                    "v": provider_version or "",
                    "now": now,
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
        """DB-backed lock — visible to every Gunicorn/worker process."""
        try:
            from sqlalchemy import text as sa_text
            now = datetime.now(timezone.utc)
            stale_before = now - timedelta(seconds=_FETCH_LOCK_STALE_SECONDS)
            self._db.execute(
                sa_text(
                    "UPDATE provider_cache SET fetch_status='idle', fetch_started_at=NULL, "
                    "locked_by=NULL WHERE provider=:p AND cache_key=:k "
                    "AND fetch_status='fetching' "
                    "AND (fetch_started_at IS NULL OR fetch_started_at < :stale)"
                ),
                {"p": self._provider, "k": key, "stale": stale_before},
            )
            result = self._db.execute(
                sa_text(
                    """
                    INSERT INTO provider_cache
                        (provider, cache_key, response_json, expires_at,
                         fetch_status, fetch_started_at, locked_by, updated_at)
                    VALUES (:p, :k, '{}', :exp, 'fetching', :now, :owner, :now)
                    ON CONFLICT (provider, cache_key) DO UPDATE
                    SET fetch_status = 'fetching',
                        fetch_started_at = :now,
                        locked_by = :owner,
                        updated_at = :now
                    WHERE provider_cache.fetch_status IS DISTINCT FROM 'fetching'
                    RETURNING id
                    """
                ),
                {
                    "p": self._provider,
                    "k": key,
                    "exp": now,
                    "now": now,
                    "owner": _PROCESS_ID,
                },
            )
            row = result.fetchone()
            self._db.commit()
            return row is not None
        except Exception:
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
                    "UPDATE provider_cache SET fetch_status='idle', fetch_started_at=NULL, "
                    "locked_by=NULL WHERE provider=:p AND cache_key=:k "
                    "AND fetch_status='fetching'"
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
    """Cache lookup with distributed coalescing + optional SWR."""
    provider = cache._provider
    db = cache._db

    if not provider_enabled(provider):
        entry = cache.get(key, allow_stale=True)
        if entry:
            record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0,
                          status="disabled", cache_hit=True)
            return entry.data
        record_metric(db, provider=provider, endpoint=endpoint, latency_ms=0, status="disabled")
        return None

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
