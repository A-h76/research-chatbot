"""HTTP security headers (PR4 + Phase 4 CSP enforce).

Baseline headers on every response. Production defaults to **enforcing**
CSP (Phase 4). Rollback: set CSP_REPORT_ONLY=1 to emit Report-Only only.
Disable entirely with CSP_DISABLE=1.
"""

from __future__ import annotations

from typing import Mapping, MutableMapping, Optional, Tuple

# Conservative policy for the production SPA served same-origin.
# Allows Google profile images + data/blob previews; keeps scripts same-origin.
PROD_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; "
    "media-src 'self' blob:"
)

# Looser policy for local Vite HMR when explicitly enabled.
DEV_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:5173 http://127.0.0.1:5173; "
    "style-src 'self' 'unsafe-inline' http://localhost:5173 http://127.0.0.1:5173; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' ws://localhost:5173 ws://127.0.0.1:5173 "
    "http://localhost:5173 http://127.0.0.1:5173; "
    "worker-src 'self' blob:; "
    "media-src 'self' blob:"
)

# Back-compat aliases
PROD_CSP_REPORT_ONLY = PROD_CSP
DEV_CSP_REPORT_ONLY = DEV_CSP


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_csp(
    *,
    is_production: bool,
    environ: Mapping[str, str],
) -> Tuple[Optional[str], bool]:
    """Return (policy, enforce).

    enforce=True → Content-Security-Policy
    enforce=False → Content-Security-Policy-Report-Only (or omit if no policy)
    """
    if _truthy(environ.get("CSP_DISABLE")) or _truthy(environ.get("CSP_REPORT_ONLY_DISABLE")):
        return None, False

    custom = (environ.get("CSP_POLICY") or environ.get("CSP_REPORT_ONLY_POLICY") or "").strip()
    if is_production:
        policy = custom or PROD_CSP
        # Phase 4: enforce by default; CSP_REPORT_ONLY=1 rolls back to report-only.
        enforce = not _truthy(environ.get("CSP_REPORT_ONLY"))
        return policy, enforce

    # Development: only when explicitly requested
    force_report = _truthy(environ.get("CSP_REPORT_ONLY"))
    force_enforce = _truthy(environ.get("CSP_ENFORCE"))
    if not (force_report or force_enforce):
        return None, False
    policy = custom or DEV_CSP
    return policy, force_enforce


def build_csp_report_only(*, is_production: bool, environ: Mapping[str, str]) -> Optional[str]:
    """Deprecated helper — prefer resolve_csp(). Kept for older tests."""
    policy, enforce = resolve_csp(is_production=is_production, environ=environ)
    if policy is None:
        return None
    if enforce:
        return None  # enforcing path uses a different header
    return policy


def _is_authenticated_surface(path: Optional[str]) -> bool:
    """API/auth JSON surfaces must not be cached by shared proxies/browsers."""
    if not path:
        return False
    return path == "/api" or path.startswith("/api/") or path == "/auth" or path.startswith("/auth/")


def apply_security_headers(
    response: MutableMapping,
    *,
    is_production: bool,
    environ: Mapping[str, str],
    request_path: Optional[str] = None,
) -> MutableMapping:
    """Mutate ``response.headers`` (Werkzeug/Flask Response) in place."""
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    )
    headers.setdefault("X-XSS-Protection", "0")

    if is_production:
        headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    if _is_authenticated_surface(request_path):
        headers.setdefault("Cache-Control", "no-store")

    policy, enforce = resolve_csp(is_production=is_production, environ=environ)
    if policy:
        if enforce:
            headers.setdefault("Content-Security-Policy", policy)
        else:
            headers.setdefault("Content-Security-Policy-Report-Only", policy)

    return response
