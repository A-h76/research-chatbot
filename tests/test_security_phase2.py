"""Phase 2 security fixes — JWT session_version, query caps, gate wiring.

Standalone Flask apps (not full server.py) so tests stay fast and DB-light.
Run: pytest tests/test_security_phase2.py -v
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from flask import Flask, g, jsonify
from flask_jwt_extended import JWTManager

from auth.decorators import jwt_required, set_jwt_session_version_checker
from auth.jwt_utils import create_jwt, decode_jwt, session_version_matches
from backend.search.routes import MAX_RAG_QUERY_CHARS, MAX_SEARCH_QUERY_CHARS, create_search_blueprint


def test_create_jwt_embeds_session_version():
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    with app.app_context():
        access, refresh = create_jwt(7, session_version=3)
        assert decode_jwt(access)["sv"] == 3
        assert decode_jwt(refresh)["sv"] == 3
        assert session_version_matches(decode_jwt(access), 3)
        assert not session_version_matches(decode_jwt(access), 4)
        assert not session_version_matches({}, 0)


def test_jwt_required_rejects_stale_session_version():
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)

    versions = {"7": 1}

    def checker(claims, identity):
        cur = versions.get(str(identity), -1)
        if not session_version_matches(claims or {}, cur):
            return jsonify({"error": "token_revoked"}), 401
        return None

    set_jwt_session_version_checker(checker)

    @app.route("/protected")
    @jwt_required()
    def protected():
        return jsonify({"uid": g.current_user})

    try:
        with app.app_context():
            good, _ = create_jwt(7, session_version=1)
            stale, _ = create_jwt(7, session_version=0)

        client = app.test_client()
        ok = client.get("/protected", headers={"Authorization": f"Bearer {good}"})
        assert ok.status_code == 200
        assert ok.get_json()["uid"] == "7"

        # Simulate logout-all
        versions["7"] = 2
        denied = client.get("/protected", headers={"Authorization": f"Bearer {good}"})
        assert denied.status_code == 401
        assert denied.get_json()["error"] == "token_revoked"

        # Stale minted sv never matches
        denied2 = client.get("/protected", headers={"Authorization": f"Bearer {stale}"})
        assert denied2.status_code == 401
    finally:
        set_jwt_session_version_checker(None)


def test_search_rejects_oversized_query(mocker):
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)

    class Gate:
        def __init__(self):
            self.calls = 0

        def preflight(self, *a, **k):
            self.calls += 1

    gate = Gate()
    app.register_blueprint(
        create_search_blueprint(
            SessionLocal=lambda: None,
            UserFile=object,
            Chunk=object,
            get_prompt_builder=lambda db: None,
            model_router=object(),
            PromptExecution=object,
            ai_gate=gate,
        )
    )
    with app.app_context():
        access, _ = create_jwt(1, session_version=0)

    client = app.test_client()
    huge = "x" * (MAX_SEARCH_QUERY_CHARS + 1)
    resp = client.get(f"/api/documents/search?q={huge}", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "query_too_long"
    assert gate.calls == 0  # rejected before AI gate / embed


def test_rag_rejects_oversized_query():
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    app.register_blueprint(
        create_search_blueprint(
            SessionLocal=lambda: None,
            UserFile=object,
            Chunk=object,
            get_prompt_builder=lambda db: None,
            model_router=object(),
            PromptExecution=object,
        )
    )
    with app.app_context():
        access, _ = create_jwt(1)

    client = app.test_client()
    resp = client.post(
        "/api/rag",
        json={"query": "y" * (MAX_RAG_QUERY_CHARS + 1)},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] in ("query_too_long", "field_too_long")


def test_rag_ai_gate_denial_short_circuits(mocker):
    from security.ops.gate import AiAccessDenied

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)

    class Gate:
        def preflight(self, *a, **k):
            raise AiAccessDenied("AI temporarily disabled", "ai_disabled", http_status=403)

    app.register_blueprint(
        create_search_blueprint(
            SessionLocal=lambda: None,
            UserFile=object,
            Chunk=object,
            get_prompt_builder=lambda db: None,
            model_router=object(),
            PromptExecution=object,
            ai_gate=Gate(),
        )
    )
    with app.app_context():
        access, _ = create_jwt(1)

    client = app.test_client()
    resp = client.post(
        "/api/rag",
        json={"query": "are widgets efficient?"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "ai_disabled"
