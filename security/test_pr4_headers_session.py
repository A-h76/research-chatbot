"""PR4 integration: security headers on responses + session TTL gate."""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture(scope="module")
def app_module():
    import server

    return server


def test_responses_include_baseline_security_headers(app_module):
    client = app_module.app.test_client()
    resp = client.get("/api/worker/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "Referrer-Policy" in resp.headers
    assert "Permissions-Policy" in resp.headers


def test_session_ttl_expires_idle_api_session(app_module, mocker):
    from security.session_ttl import SESSION_ACTIVITY_KEY, SESSION_STARTED_KEY

    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        started = datetime.now(timezone.utc) - timedelta(hours=2)
        sess[SESSION_STARTED_KEY] = started.isoformat()
        sess[SESSION_ACTIVITY_KEY] = started.isoformat()

    mocker.patch.dict(
        "os.environ",
        {"SESSION_IDLE_MINUTES": "30", "SESSION_ABSOLUTE_HOURS": "12"},
        clear=False,
    )
    logged = mocker.patch.object(app_module, "log_security_event")
    resp = client.get("/api/me")
    assert resp.status_code == 401
    body = resp.get_json() or {}
    assert body.get("error") in ("session_expired", "not_authenticated")
    if body.get("error") == "session_expired":
        logged.assert_any_call("session_expired", reason="idle", path="/api/me")
