"""HTTP security headers (PR4).

Baseline headers on every response. CSP is Report-Only in production by
default so we can observe violations without breaking the SPA / OAuth /
SSE / KaTeX paths. Development skips CSP unless CSP_REPORT_ONLY=1.
"""

from __future__ import annotations

from typing import Mapping, MutableMapping, Optional

# Conservative Report-Only policy for the production SPA served same-origin.
# Allows Google profile images + data/blob previews; keeps scripts same-origin.
PROD_CSP_REPORT_ONLY = (
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

# Looser Report-Only for local Vite HMR when explicitly enabled.
DEV_CSP_REPORT_ONLY = (
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


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def build_csp_report_only(*, is_production: bool, environ: Mapping[str, str]) -> Optional[str]:
    """Return a Report-Only CSP string, or None to omit the header."""
    force = _truthy(environ.get("CSP_REPORT_ONLY"))
    disable = _truthy(environ.get("CSP_REPORT_ONLY_DISABLE"))
    if disable:
        return None
    if is_production or force:
        if is_production:
            return (environ.get("CSP_REPORT_ONLY_POLICY") or "").strip() or PROD_CSP_REPORT_ONLY
        return (environ.get("CSP_REPORT_ONLY_POLICY") or "").strip() or DEV_CSP_REPORT_ONLY
    return None


def apply_security_headers(
    response: MutableMapping,
    *,
    is_production: bool,
    environ: Mapping[str, str],
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
    # Disable legacy XSS auditor (modern browsers ignore/remove it).
    headers.setdefault("X-XSS-Protection", "0")

    if is_production:
        headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    csp = build_csp_report_only(is_production=is_production, environ=environ)
    if csp:
        headers.setdefault("Content-Security-Policy-Report-Only", csp)

    return response
