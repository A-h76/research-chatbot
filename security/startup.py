"""Production startup and rate-limiter configuration (PR1 hardening).

No AI / Phase-1 / PromptBuilder changes — config and abuse controls only.
"""

from __future__ import annotations

import logging
from typing import Mapping, MutableMapping, Optional

log = logging.getLogger(__name__)


def is_production_env(environ: Mapping[str, str]) -> bool:
    return (
        (environ.get("FLASK_ENV") or "").lower() == "production"
        or (environ.get("APP_ENV") or "").lower() == "production"
    )


def _r2_is_configured(environ: Mapping[str, str]) -> bool:
    provider = (environ.get("STORAGE_PROVIDER") or "").strip().lower()
    bucket = (environ.get("R2_BUCKET") or "").strip()
    account_id = (environ.get("R2_ACCOUNT_ID") or "").strip()
    endpoint = (environ.get("R2_ENDPOINT") or "").strip() or (
        f"https://{account_id}.r2.cloudflarestorage.com" if account_id else ""
    )
    if provider == "local":
        return False
    if provider == "r2":
        return True
    return bool(bucket and endpoint)


def require_production_secrets(
    environ: Mapping[str, str],
    *,
    is_production: Optional[bool] = None,
) -> None:
    """Refuse to start in production when required secrets are missing.

    Never silently invent FLASK_SECRET_KEY / JWT secrets in production.
    Raises SystemExit with a clear message (suitable at import/boot).
    """
    if is_production is None:
        is_production = is_production_env(environ)
    if not is_production:
        return

    missing: list[str] = []

    if (environ.get("DEV_AUTO_LOGIN") or "").strip():
        raise SystemExit(
            "Production startup refused: DEV_AUTO_LOGIN must not be set when "
            "FLASK_ENV/APP_ENV is production."
        )

    if not (environ.get("FLASK_SECRET_KEY") or "").strip():
        missing.append("FLASK_SECRET_KEY")

    # JWT may inherit FLASK_SECRET_KEY; require at least one explicit secret.
    if not (environ.get("JWT_SECRET_KEY") or "").strip() and not (
        environ.get("FLASK_SECRET_KEY") or ""
    ).strip():
        missing.append("JWT_SECRET_KEY")

    if not (environ.get("GOOGLE_CLIENT_ID") or "").strip():
        missing.append("GOOGLE_CLIENT_ID")
    if not (environ.get("GOOGLE_CLIENT_SECRET") or "").strip():
        missing.append("GOOGLE_CLIENT_SECRET")

    # Phase 3: refuse to boot without a provider key — silent mid-request
    # failures are worse than a clear startup refusal.
    if not (environ.get("OPENAI_API_KEY") or "").strip():
        missing.append("OPENAI_API_KEY")

    if not (environ.get("RESEND_API_KEY") or "").strip():
        missing.append("RESEND_API_KEY")

    if not (environ.get("REDIS_URL") or "").strip():
        redis_memory_ok = (environ.get("RATE_LIMIT_MEMORY_OK") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if redis_memory_ok:
            log.warning(
                "REDIS_URL unset in production (RATE_LIMIT_MEMORY_OK=1) — Flask-Limiter "
                "uses memory://; limits are NOT shared across workers or instances."
            )
        else:
            # Multi-worker / multi-instance deploys need shared limiter storage.
            missing.append(
                "REDIS_URL (or set RATE_LIMIT_MEMORY_OK=1 for single-process only)"
            )

    clam = (environ.get("CLAMAV_ENABLED") or "").strip().lower()
    clam_on = clam in {"1", "true", "yes", "on"}
    clam_optional = (environ.get("CLAMAV_OPTIONAL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not clam_on:
        if clam_optional:
            log.warning(
                "CLAMAV_ENABLED is off in production (CLAMAV_OPTIONAL=1) — uploads are "
                "magic-byte validated but not virus-scanned."
            )
        else:
            # Phase 4: require ClamAV unless explicitly opted out.
            missing.append("CLAMAV_ENABLED (or set CLAMAV_OPTIONAL=1 to acknowledge risk)")
    else:
        log.info("CLAMAV_ENABLED is on — upload virus scanning required.")

    if _r2_is_configured(environ):
        for key in ("R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
            if not (environ.get(key) or "").strip():
                missing.append(key)
        account_id = (environ.get("R2_ACCOUNT_ID") or "").strip()
        endpoint = (environ.get("R2_ENDPOINT") or "").strip()
        if not endpoint and not account_id:
            missing.append("R2_ENDPOINT or R2_ACCOUNT_ID")

    if missing:
        raise SystemExit(
            "Production startup refused: missing required environment variables: "
            + ", ".join(missing)
            + ". Set them explicitly; secrets are never auto-generated in production."
        )


def resolve_flask_secret_key(
    environ: Mapping[str, str],
    *,
    is_production: Optional[bool] = None,
) -> str:
    """Return the Flask secret key. Ephemeral random only allowed outside production."""
    if is_production is None:
        is_production = is_production_env(environ)
    explicit = (environ.get("FLASK_SECRET_KEY") or "").strip()
    if explicit:
        return explicit
    if is_production:
        raise SystemExit(
            "Production startup refused: FLASK_SECRET_KEY is required "
            "(refusing silent random generation)."
        )
    import os as _os

    key = _os.urandom(32).hex()
    log.warning(
        "FLASK_SECRET_KEY unset; using ephemeral in-memory key (development only). "
        "Sessions and signed URLs will reset on restart."
    )
    return key


def resolve_limiter_storage_uri(
    redis_url: str,
    *,
    is_production: bool,
) -> str:
    """Use Redis for Flask-Limiter when REDIS_URL is set and reachable.

    Development: fall back to memory:// if Redis is missing or unreachable.
    Production without REDIS_URL: memory:// only after RATE_LIMIT_MEMORY_OK
    was acknowledged at ``require_production_secrets`` (single-process).
    Production with REDIS_URL unreachable: fall back to memory:// and log
    an error (prefer a live site over Cloudflare 524 crash-loops).
    """
    url = (redis_url or "").strip()
    if not url:
        if is_production:
            log.warning(
                "REDIS_URL unset in production — rate limiter using memory:// "
                "(limits will not be shared across workers)."
            )
        return "memory://"

    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        try:
            client.ping()
        finally:
            client.close()
        return url
    except Exception as exc:
        # Prefer a live app with process-local limits over Cloudflare 524 /
        # crash-loop when Redis is briefly unreachable after deploy.
        log.error(
            "REDIS_URL is set but Redis is unreachable (%s) — "
            "falling back to memory:// rate limiter (limits NOT shared "
            "across workers). Fix Redis ASAP.",
            exc,
        )
        return "memory://"
