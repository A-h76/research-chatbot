"""Tests for backend/prompts/routes.py — session-authenticated (not JWT,
matching this blueprint's own login_required + admin_required gating),
standalone Flask app + in-memory SQLite. PromptRegistry/PersonaEngine are
real (both already fully tested in their own files — backend/ai/
test_prompt_registry.py, test_persona_engine.py); PromptBuilder is
mocked here, same reasoning as backend/search/test_search.py: its own
assembly logic is backend/ai/test_prompt_builder.py's job, not this
file's.

login_required here is a small local stand-in (session-based 401), not
server.py's real one — that one calls url_for("login_page"), which
doesn't exist in a standalone test app with no such route registered.
admin_required is the real create_admin_required() from
auth/decorators.py — it's already a proper, injectable factory, nothing
to fake.

Run: pytest backend/prompts/test_routes.py -v
"""

from functools import wraps

import pytest
from flask import Flask, jsonify, session
from sqlalchemy import Boolean, Column, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from auth.decorators import create_admin_required
from backend.ai.persona_engine import PersonaEngine
from backend.ai.prompt_builder import AssembledPrompt
from backend.ai.prompt_registry import Persona, PromptRegistry, PromptVersion
from backend.ai.prompt_registry import _Base as prompt_base
from backend.prompts.routes import create_prompts_blueprint


def _login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "not_authenticated"}), 401
        return f(*args, **kwargs)

    return wrapper


@pytest.fixture
def env(mocker):
    engine = create_engine("sqlite:///:memory:")
    prompt_base.metadata.create_all(engine)  # prompt_versions + personas

    UserBase = declarative_base()

    class User(UserBase):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        is_admin = Column(Boolean, default=False)

    UserBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    db = SessionLocal()
    admin_user = User(id=1, is_admin=True)
    plain_user = User(id=2, is_admin=False)
    db.add_all([admin_user, plain_user])
    db.commit()
    db.close()

    fake_builder = mocker.Mock()
    fake_builder.preview.return_value = AssembledPrompt(
        system="sys",
        persona="",
        project_context="",
        memory="",
        rag="",
        task="task text",
        output_schema="",
        final="FINAL PREVIEW TEXT",
        prompt_version_id=1,
        persona_id=None,
    )

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(
        create_prompts_blueprint(
            SessionLocal=SessionLocal,
            PromptVersion=PromptVersion,
            Persona=Persona,
            PromptRegistry=PromptRegistry,
            PersonaEngine=PersonaEngine,
            get_prompt_builder=lambda db_session: fake_builder,
            login_required=_login_required,
            admin_required=create_admin_required(SessionLocal, User),
        )
    )

    return {"client": app.test_client(), "SessionLocal": SessionLocal, "fake_builder": fake_builder}


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ------------------------------------------------------------ auth gating
def test_list_prompts_requires_login(env):
    resp = env["client"].get("/api/prompts")
    assert resp.status_code == 401


def test_create_prompt_requires_login(env):
    resp = env["client"].post("/api/prompts", json={"name": "x", "template": "y"})
    assert resp.status_code == 401


def test_create_prompt_requires_admin(env):
    _login(env["client"], 2)  # logged in, not admin
    resp = env["client"].post("/api/prompts", json={"name": "x", "template": "y"})
    assert resp.status_code == 403


def test_create_prompt_succeeds_for_admin(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/prompts", json={"name": "x", "template": "y"})
    assert resp.status_code == 201, resp.get_json()


# ------------------------------------------------------------ prompts: read
def test_list_prompts_returns_created_prompts(env):
    _login(env["client"], 1)
    env["client"].post("/api/prompts", json={"name": "a", "template": "A", "category": "cat1"})
    env["client"].post("/api/prompts", json={"name": "b", "template": "B", "category": "cat2"})

    resp = env["client"].get("/api/prompts")
    names = {p["name"] for p in resp.get_json()["prompts"]}
    assert names == {"a", "b"}


def test_list_prompts_filters_by_category(env):
    _login(env["client"], 1)
    env["client"].post("/api/prompts", json={"name": "a", "template": "A", "category": "cat1"})
    env["client"].post("/api/prompts", json={"name": "b", "template": "B", "category": "cat2"})

    resp = env["client"].get("/api/prompts?category=cat1")
    names = {p["name"] for p in resp.get_json()["prompts"]}
    assert names == {"a"}


def test_list_prompts_filters_by_status(env):
    _login(env["client"], 1)
    env["client"].post("/api/prompts", json={"name": "a", "template": "A", "status": "active"})
    env["client"].post("/api/prompts", json={"name": "b", "template": "B"})  # draft default

    resp = env["client"].get("/api/prompts?status=active")
    names = {p["name"] for p in resp.get_json()["prompts"]}
    assert names == {"a"}


def test_get_prompt_by_id(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()

    resp = env["client"].get(f"/api/prompts/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "a"


def test_get_prompt_not_found(env):
    _login(env["client"], 1)
    resp = env["client"].get("/api/prompts/999999")
    assert resp.status_code == 404


# ------------------------------------------------------------ prompts: create
def test_create_prompt_missing_fields_returns_400(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/prompts", json={"name": "a"})  # no template
    assert resp.status_code == 400


def test_create_prompt_duplicate_name_returns_409(env):
    _login(env["client"], 1)
    env["client"].post("/api/prompts", json={"name": "a", "template": "A"})
    resp = env["client"].post("/api/prompts", json={"name": "a", "template": "A2"})
    assert resp.status_code == 409


def test_create_prompt_defaults_to_draft(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/prompts", json={"name": "a", "template": "A"})
    body = resp.get_json()
    assert body["status"] == "draft"
    assert body["is_active"] is False


def test_create_prompt_stores_examples_and_metadata(env):
    _login(env["client"], 1)
    resp = env["client"].post(
        "/api/prompts",
        json={
            "name": "a",
            "template": "A",
            "description": "desc",
            "category": "cat",
            "expected_output_type": "json",
            "examples": [{"input": "x", "output": "y"}],
        },
    )
    body = resp.get_json()
    assert body["description"] == "desc"
    assert body["category"] == "cat"
    assert body["expected_output_type"] == "json"
    assert body["examples"] == [{"input": "x", "output": "y"}]


# ------------------------------------------------------------ prompts: update
def test_update_prompt_requires_admin(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()
    _login(env["client"], 2)
    resp = env["client"].patch(f"/api/prompts/{created['id']}", json={"description": "new"})
    assert resp.status_code == 403


def test_update_prompt_changes_metadata_fields(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()

    resp = env["client"].patch(
        f"/api/prompts/{created['id']}",
        json={
            "description": "updated desc",
            "category": "new-cat",
        },
    )
    body = resp.get_json()
    assert body["description"] == "updated desc"
    assert body["category"] == "new-cat"


def test_update_prompt_status_active_activates_it(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()

    resp = env["client"].patch(f"/api/prompts/{created['id']}", json={"status": "active"})
    body = resp.get_json()
    assert body["status"] == "active"
    assert body["is_active"] is True


def test_update_prompt_not_found(env):
    _login(env["client"], 1)
    resp = env["client"].patch("/api/prompts/999999", json={"description": "x"})
    assert resp.status_code == 404


# ------------------------------------------------------------ prompts: versions
def test_create_version_requires_admin(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()
    _login(env["client"], 2)
    resp = env["client"].post(f"/api/prompts/{created['id']}/versions", json={"template": "A2"})
    assert resp.status_code == 403


def test_create_version_increments_version_number(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()

    resp = env["client"].post(f"/api/prompts/{created['id']}/versions", json={"template": "A2"})
    body = resp.get_json()
    assert body["version"] == 2
    assert body["template"] == "A2"


def test_create_version_missing_template_returns_400(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()
    resp = env["client"].post(f"/api/prompts/{created['id']}/versions", json={})
    assert resp.status_code == 400


def test_create_version_not_found(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/prompts/999999/versions", json={"template": "A2"})
    assert resp.status_code == 404


def test_create_version_is_active_without_status_active_returns_400(env):
    _login(env["client"], 1)
    created = env["client"].post("/api/prompts", json={"name": "a", "template": "A"}).get_json()
    # is_active=True with the default status="draft" violates the state
    # machine (PromptRegistry.add_version) — the route surfaces that as
    # a 400, not a 500.
    resp = env["client"].post(f"/api/prompts/{created['id']}/versions", json={"template": "A2", "is_active": True})
    assert resp.status_code == 400


# ------------------------------------------------------------ preview
def test_preview_requires_login(env):
    resp = env["client"].post("/api/prompts/preview", json={"task_name": "x"})
    assert resp.status_code == 401


def test_preview_does_not_require_admin(env):
    _login(env["client"], 2)  # logged in, not admin
    resp = env["client"].post("/api/prompts/preview", json={"task_name": "x", "user_query": "q"})
    assert resp.status_code == 200


def test_preview_missing_task_name_returns_400(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/prompts/preview", json={})
    assert resp.status_code == 400


def test_preview_returns_assembled_prompt_fields(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/prompts/preview", json={"task_name": "x", "user_query": "q"})
    body = resp.get_json()
    assert body["final"] == "FINAL PREVIEW TEXT"
    assert body["prompt_version_id"] == 1


def test_preview_uses_session_user_id_not_client_supplied_one(env):
    # Security: the logged-in user's own id is used for memory lookups,
    # never whatever a client puts in the request body.
    _login(env["client"], 2)
    env["client"].post(
        "/api/prompts/preview",
        json={"task_name": "x", "user_query": "q", "user_id": 999999},
    )
    call = env["fake_builder"].preview.call_args
    assert call.kwargs["user_id"] == 2


# ------------------------------------------------------------ personas
def test_list_personas_requires_login(env):
    resp = env["client"].get("/api/personas")
    assert resp.status_code == 401


def test_create_persona_requires_admin(env):
    _login(env["client"], 2)
    resp = env["client"].post("/api/personas", json={"name": "X", "system_prompt": "You are X."})
    assert resp.status_code == 403


def test_create_persona_succeeds_for_admin(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/personas", json={"name": "X", "system_prompt": "You are X."})
    assert resp.status_code == 201
    assert resp.get_json()["is_active"] is True


def test_create_persona_duplicate_name_returns_409(env):
    _login(env["client"], 1)
    env["client"].post("/api/personas", json={"name": "X", "system_prompt": "You are X."})
    resp = env["client"].post("/api/personas", json={"name": "X", "system_prompt": "different"})
    assert resp.status_code == 409


def test_create_persona_missing_fields_returns_400(env):
    _login(env["client"], 1)
    resp = env["client"].post("/api/personas", json={"name": "X"})  # no system_prompt
    assert resp.status_code == 400


def test_list_personas_returns_only_active(env):
    _login(env["client"], 1)
    env["client"].post("/api/personas", json={"name": "Active", "system_prompt": "sp"})

    resp = env["client"].get("/api/personas")
    names = {p["name"] for p in resp.get_json()["personas"]}
    assert names == {"Active"}
