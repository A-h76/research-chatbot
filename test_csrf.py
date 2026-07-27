"""Tests for server.py's csrf_protect() before_request hook, in particular
DEV_FRONTEND_ORIGINS — the allowance that lets `npm run dev` (Vite,
localhost:5173) call /api/* through its proxy without every state-changing
request 403ing as csrf_origin_mismatch (Vite's own origin isn't
request.host or APP_BASE_URL). DATABASE_URL isolation lives in the
project's root conftest.py (see test_worker_health.py's docstring).

Run: pytest test_csrf.py -v
"""

import server


def client():
    return server.app.test_client()


def test_get_ignores_origin():
    resp = client().get("/api/worker/health", headers={"Origin": "http://evil.com"})
    assert resp.get_json().get("error") != "csrf_origin_mismatch"


def test_no_origin_or_referer_passes():
    resp = client().post("/api/dev-login")
    assert resp.get_json().get("error") != "csrf_origin_mismatch"


def test_mismatched_origin_is_blocked():
    resp = client().post("/api/dev-login", headers={"Origin": "http://evil.com"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "csrf_origin_mismatch"


def test_same_origin_as_backend_passes():
    resp = client().post("/api/dev-login", headers={"Origin": "http://localhost"})
    assert resp.get_json().get("error") != "csrf_origin_mismatch"


def test_vite_dev_origin_blocked_when_dev_frontend_origins_empty(monkeypatch):
    """Production posture: DEV_FRONTEND_ORIGINS empty -> Vite's origin is
    treated as a mismatched origin."""
    monkeypatch.setattr(server, "DEV_FRONTEND_ORIGINS", set())
    resp = client().post("/api/dev-login", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "csrf_origin_mismatch"


def test_vite_dev_origin_allowed_when_dev_frontend_origins_set(monkeypatch):
    """The regression this file exists for: with DEV_FRONTEND_ORIGINS
    populated, a request proxied through Vite's dev server must not be
    treated as cross-origin."""
    monkeypatch.setattr(server, "DEV_FRONTEND_ORIGINS", {"localhost:5173"})
    resp = client().post("/api/dev-login", headers={"Origin": "http://localhost:5173"})
    assert resp.get_json().get("error") != "csrf_origin_mismatch"


def test_vite_fallback_port_allowed_in_non_production():
    """Vite bumps to 5174/5175/… when 5173 is busy — those origins must also pass."""
    if server.IS_PRODUCTION:
        assert server.DEV_FRONTEND_ORIGINS == set()
        return
    assert "localhost:5175" in server.DEV_FRONTEND_ORIGINS
    assert "127.0.0.1:5175" in server.DEV_FRONTEND_ORIGINS
    resp = client().post("/api/dev-login", headers={"Origin": "http://localhost:5175"})
    assert resp.get_json().get("error") != "csrf_origin_mismatch"
