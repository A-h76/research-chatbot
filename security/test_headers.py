"""Unit tests for security headers (PR4)."""

from types import SimpleNamespace

from security.headers import apply_security_headers, build_csp_report_only


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
    assert "Content-Security-Policy-Report-Only" not in resp.headers


def test_hsts_and_csp_report_only_in_production():
    resp = _response()
    apply_security_headers(resp, is_production=True, environ={})
    assert resp.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Content-Security-Policy-Report-Only" in resp.headers
    csp = resp.headers["Content-Security-Policy-Report-Only"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_csp_force_in_dev():
    assert build_csp_report_only(is_production=False, environ={}) is None
    csp = build_csp_report_only(
        is_production=False, environ={"CSP_REPORT_ONLY": "1"}
    )
    assert csp is not None
    assert "localhost:5173" in csp


def test_csp_can_be_disabled():
    assert (
        build_csp_report_only(
            is_production=True, environ={"CSP_REPORT_ONLY_DISABLE": "1"}
        )
        is None
    )
