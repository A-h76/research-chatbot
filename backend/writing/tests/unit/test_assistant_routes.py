"""Unit tests for Writing Assistant ACR routing (Bite 3)."""

from __future__ import annotations

import json

import pytest
from flask import Flask, session

from backend.ai.ai_ledger import clear_ledger_for_tests, recent_executions
from backend.writing.api.assistant_routes import create_writing_assistant_blueprint


class _FakeGateway:
    def __init__(self, content: str = "Rewritten text."):
        self.content = content
        self.calls: list[dict] = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "content": self.content,
            "total_tokens": 20,
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "cost": 0.002,
        }


class _FakeRegistry:
    pass


class _FakeSessionLocal:
    def __call__(self):
        return self

    def close(self):
        return None


@pytest.fixture
def assistant_client():
    app = Flask(__name__)
    app.secret_key = "test"
    gateway = _FakeGateway()
    bp = create_writing_assistant_blueprint(
        login_required=lambda f: f,
        limiter=type("L", (), {"limit": lambda self, *a, **k: (lambda f: f)})(),
        ai_gateway=gateway,
        SessionLocal=_FakeSessionLocal(),
        get_model_registry=lambda db: _FakeRegistry(),
    )
    app.register_blueprint(bp)

    @app.before_request
    def _seed_session():
        session["user_id"] = 42

    client = app.test_client()
    client._gateway = gateway  # type: ignore[attr-defined]
    return client


def test_writing_assistant_routes_through_gateway(assistant_client):
    clear_ledger_for_tests()
    resp = assistant_client.post(
        "/api/writing",
        data=json.dumps({"action": "improve_grammar", "text": "This are bad."}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["result"] == "Rewritten text."
    assert body["action"] == "improve_grammar"
    assert body.get("ai_execution")
    assert assistant_client._gateway.calls  # type: ignore[attr-defined]
    call = assistant_client._gateway.calls[0]  # type: ignore[attr-defined]
    assert call["user_id"] == 42
    assert call["model"]
    ledger = recent_executions(limit=1)[0]
    assert ledger["trace_id"]
    assert ledger["status"] == "completed"
    assert ledger["extra"]["action"] == "improve_grammar"


def test_writing_assistant_rejects_invalid_action(assistant_client):
    resp = assistant_client.post(
        "/api/writing",
        data=json.dumps({"action": "not_real", "text": "hello"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_writing_assistant_requires_gateway():
    app = Flask(__name__)
    app.secret_key = "test"
    bp = create_writing_assistant_blueprint(
        login_required=lambda f: f,
        limiter=type("L", (), {"limit": lambda self, *a, **k: (lambda f: f)})(),
        ai_gateway=None,
        SessionLocal=_FakeSessionLocal(),
        get_model_registry=lambda db: _FakeRegistry(),
    )
    app.register_blueprint(bp)

    @app.before_request
    def _seed_session():
        session["user_id"] = 42

    client = app.test_client()
    resp = client.post(
        "/api/writing",
        data=json.dumps({"action": "shorten", "text": "hello world"}),
        content_type="application/json",
    )
    assert resp.status_code == 503


def test_writing_assistant_requires_text(assistant_client):
    resp = assistant_client.post(
        "/api/writing",
        data=json.dumps({"action": "shorten"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
