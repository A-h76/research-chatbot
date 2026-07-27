"""Gate Prometheus /metrics exposition (PR2).

Policy:
  - If METRICS_TOKEN is set: require ``Authorization: Bearer <token>``
    (constant-time compare). Localhost is not an automatic bypass when a
    token is configured — scrapers must present the token.
  - If METRICS_TOKEN is unset: allow only loopback clients (127.0.0.0/8, ::1).
    Development may set METRICS_ALLOW_UNAUTHENTICATED=1 to keep open scrapes.
"""

from __future__ import annotations

import hmac
import ipaddress
from typing import Mapping, Optional, Tuple


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def is_loopback_remote(remote_addr: Optional[str]) -> bool:
    if not remote_addr:
        return False
    try:
        return ipaddress.ip_address(remote_addr.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def check_metrics_access(
    *,
    authorization: Optional[str],
    remote_addr: Optional[str],
    environ: Mapping[str, str],
) -> Tuple[bool, str]:
    """Return ``(allowed, reason)`` for a metrics scrape attempt."""
    token = (environ.get("METRICS_TOKEN") or "").strip()
    if token:
        presented = _extract_bearer(authorization)
        if presented and hmac.compare_digest(presented, token):
            return True, "token"
        return False, "bad_or_missing_token"

    if is_loopback_remote(remote_addr):
        return True, "loopback"

    allow_open = (environ.get("METRICS_ALLOW_UNAUTHENTICATED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if allow_open:
        return True, "allow_unauthenticated"

    return False, "denied"
