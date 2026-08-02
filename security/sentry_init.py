"""Optional Sentry error reporting (V1 #20).

Init only when ``SENTRY_DSN`` is set. Closed beta may omit it; prefer
wiring before open Alpha traffic. Never required for boot.
"""

from __future__ import annotations

import logging
from typing import Mapping, Optional

log = logging.getLogger(__name__)


def init_sentry(
    environ: Optional[Mapping[str, str]] = None,
    *,
    flask_app=None,
) -> bool:
    """Initialise Sentry if ``SENTRY_DSN`` is present.

    Returns True when SDK init ran successfully, False when skipped or failed.
    Failures are logged and never raise — observability must not block boot.
    """
    import os

    env: Mapping[str, str] = environ if environ is not None else os.environ
    dsn = (env.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:
        log.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed — "
            "pip install 'sentry-sdk[flask]' or clear SENTRY_DSN."
        )
        return False

    try:
        sample = float((env.get("SENTRY_TRACES_SAMPLE_RATE") or "0").strip() or "0")
    except ValueError:
        sample = 0.0

    environment = (
        (env.get("SENTRY_ENVIRONMENT") or "").strip()
        or (env.get("APP_ENV") or "").strip()
        or (env.get("FLASK_ENV") or "").strip()
        or "development"
    )

    try:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=max(0.0, min(sample, 1.0)),
            environment=environment,
            send_default_pii=False,
        )
        if flask_app is not None:
            # Ensure Flask app is bound even if init ran before create_app-style wiring.
            flask_app.config.setdefault("SENTRY_DSN", dsn)
        log.info("Sentry error reporting enabled (environment=%s)", environment)
        return True
    except Exception as exc:
        log.warning("Sentry init failed (%s) — continuing without it", exc)
        return False
