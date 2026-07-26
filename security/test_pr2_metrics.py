"""PR2 integration: /metrics gate + chat ownership hardening surface."""

import os

import pytest


@pytest.fixture(scope="module")
def app_module():
    import server

    return server


def test_metrics_allows_loopback_without_token(app_module, monkeypatch):
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    monkeypatch.delenv("METRICS_ALLOW_UNAUTHENTICATED", raising=False)
    client = app_module.app.test_client()
    resp = client.get("/metrics", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert resp.status_code == 200
    assert b"http_requests_total" in resp.data or b"# HELP" in resp.data


def test_metrics_denies_remote_without_token(app_module, monkeypatch, mocker):
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    monkeypatch.delenv("METRICS_ALLOW_UNAUTHENTICATED", raising=False)
    logged = mocker.patch.object(app_module, "log_security_event")
    client = app_module.app.test_client()
    resp = client.get("/metrics", environ_base={"REMOTE_ADDR": "203.0.113.10"})
    assert resp.status_code == 401
    logged.assert_called()
    assert logged.call_args[0][0] == "metrics_access_denied"


def test_metrics_accepts_bearer_token(app_module, monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "pr2-test-token")
    monkeypatch.delenv("METRICS_ALLOW_UNAUTHENTICATED", raising=False)
    client = app_module.app.test_client()
    resp = client.get(
        "/metrics",
        headers={"Authorization": "Bearer pr2-test-token"},
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
    )
    assert resp.status_code == 200


def test_legacy_assembler_drops_cross_owned_project(app_module):
    class U:
        id = 1
        name = "A"
        custom_instructions = ""

    class P:
        id = 9
        user_id = 2
        name = "Secret"
        instructions = "LEAK_ME"

    text = app_module._build_system_prompt_legacy(U(), P(), memory_enabled=False)
    assert "LEAK_ME" not in text
    assert "Secret" not in text
