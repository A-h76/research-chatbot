"""Unit tests for security headers (PR4 + Phase 4 CSP enforce)."""

from types import SimpleNamespace

from security.headers import apply_security_headers, build_csp_report_only, resolve_csp


def _response():
    return SimpleNamespace(headers={})


def test_baseline_headers_always_set():
    resp = _response()
    apply_security_headers(resp, is_production=False, environ={})
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in resp.headers
    assert "Permissions-Policy" in resp.headers
    assert "Strict-Transport-Security" not in resp.headers
    assert "Content-Security-Policy" not in resp.headers
    assert "Content-Security-Policy-Report-Only" not in resp.headers


def test_hsts_and_csp_enforced_in_production():
    resp = _response()
    apply_security_headers(resp, is_production=True, environ={})
    assert resp.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Content-Security-Policy" in resp.headers
    assert "Content-Security-Policy-Report-Only" not in resp.headers
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "static.cloudflareinsights.com" in csp
    assert "cloudflareinsights.com" in csp


def test_csp_report_only_rollback():
    resp = _response()
    apply_security_headers(resp, is_production=True, environ={"CSP_REPORT_ONLY": "1"})
    assert "Content-Security-Policy-Report-Only" in resp.headers
    assert "Content-Security-Policy" not in resp.headers


def test_api_paths_get_no_store_cache_control():
    resp = _response()
    apply_security_headers(
        resp, is_production=False, environ={}, request_path="/api/files"
    )
    assert resp.headers["Cache-Control"] == "no-store"


def test_static_paths_skip_no_store():
    resp = _response()
    apply_security_headers(
        resp, is_production=False, environ={}, request_path="/assets/app.js"
    )
    assert "Cache-Control" not in resp.headers


def test_csp_force_in_dev():
    assert build_csp_report_only(is_production=False, environ={}) is None
    csp = build_csp_report_only(
        is_production=False, environ={"CSP_REPORT_ONLY": "1"}
    )
    assert csp is not None
    assert "localhost:5173" in csp
    policy, enforce = resolve_csp(
        is_production=False, environ={"CSP_ENFORCE": "1"}
    )
    assert policy is not None
    assert enforce is True


def test_csp_can_be_disabled():
    assert (
        build_csp_report_only(
            is_production=True, environ={"CSP_REPORT_ONLY_DISABLE": "1"}
        )
        is None
    )
    policy, _ = resolve_csp(is_production=True, environ={"CSP_DISABLE": "1"})
    assert policy is None
