"""Scholarly provider integrations — shared utilities.

Each provider module uses this module's:
- ProviderCache  for get/set with automatic expiry
- provider_get   for HTTP with timeout + retry + polite headers
- Soft-fail contract: every public function returns None on any error;
  callers must treat None as "unavailable, continue without enrichment".
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        f"Soro/1.0 (Research OS; mailto:{os.environ.get('CROSSREF_MAILTO', 'admin@soro.app')})"
    ),
    "Accept": "application/json",
})


def provider_get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 5,
    retries: int = 1,
) -> dict[str, Any] | None:
    """GET with timeout + 1 retry.  Returns None on any failure."""
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                logger.warning("provider_get rate-limited: %s", url)
                return None
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt == retries:
                logger.warning("provider_get failed (%s): %s", url, exc)
                return None
            time.sleep(0.5)
    return None


def cache_key_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:48]


class ProviderCache:
    """DB-backed cache — one row per (provider, key).

    Uses the provider_cache table created by migration 0018.
    Falls back gracefully if the table doesn't exist yet (SQLite local dev).
    """

    def __init__(self, db: Any, provider: str) -> None:
        self._db = db
        self._provider = provider

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            from sqlalchemy import text as sa_text
            row = self._db.execute(
                sa_text(
                    "SELECT response_json, expires_at FROM provider_cache "
                    "WHERE provider=:p AND cache_key=:k LIMIT 1"
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
            if expires_at < datetime.now(timezone.utc):
                return None
            return json.loads(row[0])
        except Exception:
            return None

    def set(self, key: str, data: dict[str, Any], ttl_hours: int = 24) -> None:
        try:
            from sqlalchemy import text as sa_text
            expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
            self._db.execute(
                sa_text(
                    "INSERT INTO provider_cache (provider, cache_key, response_json, expires_at, updated_at) "
                    "VALUES (:p, :k, :r, :e, NOW()) "
                    "ON CONFLICT (provider, cache_key) DO UPDATE "
                    "SET response_json=:r, expires_at=:e, updated_at=NOW()"
                ),
                {
                    "p": self._provider,
                    "k": key,
                    "r": json.dumps(data, ensure_ascii=False),
                    "e": expires,
                },
            )
            self._db.commit()
        except Exception as exc:
            logger.debug("ProviderCache.set failed silently: %s", exc)
