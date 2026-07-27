"""Tests for GET /api/documents/search and POST /api/rag — standalone
Flask app + in-memory SQLite (not server.py, avoids needing a live DB).

POST /api/rag now builds its prompt via PromptBuilder rather than calling
PromptRegistry directly — mocked here (a real one is already covered by
backend/ai/test_prompt_builder.py's 20 tests; re-testing its internal
assembly here would just duplicate that, not test what this route
actually does). ModelRegistry is mocked for the same "already tested
elsewhere" reason. ModelRouter is real (backend/ai/test_model_router.py
already covers it, and it's trivial to construct — no reason to fake
something this cheap). ensure_default_prompts is mocked because this
fixture's schema has no prompt_versions table at all — that function
would otherwise hit "no such table" against this file's minimal DB, not
because its behavior needs stubbing.

Chunk embeddings are real Python lists scored with the module's own real
_cosine(), not mocked — the point of the search tests is verifying the
ranking/filtering logic actually works, not just that a mock was called.

Run: pytest backend/search/test_search.py -v
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from auth.jwt_utils import create_jwt
from backend.ai import ModelError
from backend.ai.model_router import ModelRouter
from backend.ai.prompt_builder import AssembledPrompt
from backend.search import routes as search_routes
from backend.search.routes import create_search_blueprint


@pytest.fixture
def env(mocker):
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        project_id = Column(Integer, nullable=True)
        kind = Column(String(20), default="document")
        title = Column(String(500))
        name = Column(String(300))

    class Chunk(Base):
        __tablename__ = "chunks"
        id = Column(Integer, primary_key=True)
        file_id = Column(Integer, ForeignKey("files.id"))
        content = Column(Text)
        embedding = Column(Text)  # JSON list[float] | null
        page = Column(Integer, nullable=True)
        section = Column(String(200), nullable=True)

    class PromptExecution(Base):
        __tablename__ = "prompt_executions"
        id = Column(Integer, primary_key=True)
        prompt_version_id = Column(Integer, nullable=True)
        persona_id = Column(Integer, nullable=True)
        project_id = Column(Integer, nullable=True)
        user_id = Column(Integer, nullable=False)
        assembled_prompt = Column(Text, nullable=False)
        output_schema = Column(Text, nullable=True)
        tokens_used = Column(Integer, nullable=True)
        latency_ms = Column(Integer, nullable=True)
        status = Column(String(20), default="pending")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    mocker.patch.object(search_routes, "ensure_default_prompts")

    fake_builder = mocker.Mock()
    fake_builder.build.return_value = AssembledPrompt(
        system="You are a research assistant.",
        persona="",
        project_context="",
        memory="",
        rag="Widgets are efficient.",
        task="Question: are widgets efficient?",
        output_schema="",
        final="ASSEMBLED FINAL PROMPT TEXT",
        prompt_version_id=5,
        persona_id=None,
    )
    model_router = ModelRouter(defaults={"rag": "gpt-4o-mini", "_default": "gpt-4o-mini"})

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    app.register_blueprint(
        create_search_blueprint(
            SessionLocal=SessionLocal,
            UserFile=UserFile,
            Chunk=Chunk,
            get_prompt_builder=lambda db: fake_builder,
            model_router=model_router,
            PromptExecution=PromptExecution,
        )
    )

    with app.app_context():
        access, _ = create_jwt(1)

    return {
        "client": app.test_client(),
        "access": access,
        "SessionLocal": SessionLocal,
        "UserFile": UserFile,
        "Chunk": Chunk,
        "PromptExecution": PromptExecution,
        "fake_builder": fake_builder,
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _add_file_with_chunk(
    env, user_id=1, title="Widget Paper", content="Widgets are efficient.", embedding=None, page=None, project_id=None
):
    db = env["SessionLocal"]()
    uf = env["UserFile"](user_id=user_id, title=title, name=f"{title}.pdf", kind="document", project_id=project_id)
    db.add(uf)
    db.flush()
    ch = env["Chunk"](
        file_id=uf.id, content=content, embedding=json.dumps(embedding) if embedding is not None else None, page=page
    )
    db.add(ch)
    db.commit()
    file_id, chunk_id = uf.id, ch.id
    db.close()
    return file_id, chunk_id


def _mock_embed(mocker, vector, side_effect=None):
    model_registry = mocker.Mock()
    if side_effect:
        model_registry.embed.side_effect = side_effect
    else:
        model_registry.embed.return_value = vector
    model_registry.call.return_value = {
        "content": "This is the answer.",
        "model": "gpt-4o-mini",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "finish_reason": "stop",
        "cost": 0.001,
    }
    mocker.patch.object(search_routes, "ModelRegistry", return_value=model_registry)
    return model_registry


# ------------------------------------------------------------ GET /api/documents/search
def test_search_ranks_by_cosine_similarity(env, mocker):
    _add_file_with_chunk(env, title="Close match", content="widgets are great", embedding=[1.0, 0.0, 0.0])
    _add_file_with_chunk(env, title="Far match", content="unrelated content", embedding=[0.0, 1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0, 0.0])  # query vector identical to "Close match"

    resp = env["client"].get("/api/documents/search?q=widgets", headers=_auth(env["access"]))

    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert len(results) == 1  # "Far match" scores 0.0, below the 0.15 threshold
    assert results[0]["title"] == "Close match"
    assert results[0]["score"] == 1.0


def test_search_skips_chunks_without_embedding(env, mocker):
    _add_file_with_chunk(env, embedding=None)  # no embedding at all
    _mock_embed(mocker, [1.0, 0.0, 0.0])

    resp = env["client"].get("/api/documents/search?q=widgets", headers=_auth(env["access"]))

    assert resp.get_json()["results"] == []


def test_search_scopes_to_requesting_user(env, mocker):
    _add_file_with_chunk(env, user_id=2, embedding=[1.0, 0.0, 0.0])  # different user
    _mock_embed(mocker, [1.0, 0.0, 0.0])

    resp = env["client"].get("/api/documents/search?q=widgets", headers=_auth(env["access"]))

    assert resp.get_json()["results"] == []


def test_search_query_too_short_returns_400(env, mocker):
    _mock_embed(mocker, [1.0])
    resp = env["client"].get("/api/documents/search?q=a", headers=_auth(env["access"]))
    assert resp.status_code == 400


def test_search_embedding_failure_returns_502(env, mocker):
    _mock_embed(mocker, None, side_effect=ModelError("no key", provider="openai", model="text-embedding-3-small"))
    resp = env["client"].get("/api/documents/search?q=widgets", headers=_auth(env["access"]))
    assert resp.status_code == 502


def test_search_requires_jwt(env):
    resp = env["client"].get("/api/documents/search?q=widgets")
    assert resp.status_code == 401


def test_search_filters_by_file_id(env, mocker):
    fid1, _ = _add_file_with_chunk(env, title="A", embedding=[1.0, 0.0])
    fid2, _ = _add_file_with_chunk(env, title="B", embedding=[1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0])

    resp = env["client"].get(f"/api/documents/search?q=widgets&file_id={fid1}", headers=_auth(env["access"]))

    results = resp.get_json()["results"]
    assert len(results) == 1
    assert results[0]["document_id"] == fid1


# ------------------------------------------------------------ POST /api/rag
def test_rag_returns_answer_and_sources(env, mocker):
    _add_file_with_chunk(
        env, title="Widget Paper", content="Widgets are efficient under low load.", embedding=[1.0, 0.0]
    )
    _mock_embed(mocker, [1.0, 0.0])

    resp = env["client"].post("/api/rag", json={"query": "are widgets efficient?"}, headers=_auth(env["access"]))

    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["answer"] == "This is the answer."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["title"] == "Widget Paper"


def test_rag_builds_prompt_via_prompt_builder_with_rag_context(env, mocker):
    _add_file_with_chunk(env, title="Widget Paper", content="Widgets are efficient.", embedding=[1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0])

    env["client"].post("/api/rag", json={"query": "are widgets efficient?"}, headers=_auth(env["access"]))

    env["fake_builder"].build.assert_called_once()
    call = env["fake_builder"].build.call_args
    assert call.args[0] == "are widgets efficient?"
    assert call.args[1] == "semantic_search"
    assert "Widgets are efficient." in call.kwargs["rag_context"]
    assert call.kwargs["user_id"] == 1


def test_rag_sends_the_assembled_final_text_to_the_model(env, mocker):
    _add_file_with_chunk(env, embedding=[1.0, 0.0])
    model_registry = _mock_embed(mocker, [1.0, 0.0])

    env["client"].post("/api/rag", json={"query": "widgets"}, headers=_auth(env["access"]))

    call = model_registry.call.call_args
    assert call.args[0] == "gpt-4o-mini"  # model_router.get_model_for_task("rag")
    assert call.args[1] == [{"role": "user", "content": "ASSEMBLED FINAL PROMPT TEXT"}]
    assert call.kwargs["prompt_version_id"] == 5


def test_rag_writes_a_successful_prompt_execution_row(env, mocker):
    _add_file_with_chunk(env, embedding=[1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0])

    env["client"].post("/api/rag", json={"query": "widgets"}, headers=_auth(env["access"]))

    db = env["SessionLocal"]()
    rows = db.query(env["PromptExecution"]).all()
    db.close()
    assert len(rows) == 1
    assert rows[0].status == "success"
    assert rows[0].prompt_version_id == 5
    assert rows[0].assembled_prompt == "ASSEMBLED FINAL PROMPT TEXT"
    assert rows[0].tokens_used == 15
    assert rows[0].user_id == 1


def test_rag_no_matching_documents_returns_empty_answer(env, mocker):
    _mock_embed(mocker, [1.0, 0.0])  # no chunks exist at all

    resp = env["client"].post("/api/rag", json={"query": "anything"}, headers=_auth(env["access"]))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["answer"] is None
    assert body["sources"] == []
    env["fake_builder"].build.assert_not_called()  # never reached — nothing to build a prompt around


def test_rag_model_error_returns_502(env, mocker):
    _add_file_with_chunk(env, embedding=[1.0, 0.0])
    model_registry = _mock_embed(mocker, [1.0, 0.0])
    model_registry.call.side_effect = ModelError("bad key", provider="openai", model="gpt-4o-mini")

    resp = env["client"].post("/api/rag", json={"query": "widgets"}, headers=_auth(env["access"]))
    assert resp.status_code == 502


def test_rag_model_error_marks_prompt_execution_failed(env, mocker):
    _add_file_with_chunk(env, embedding=[1.0, 0.0])
    model_registry = _mock_embed(mocker, [1.0, 0.0])
    model_registry.call.side_effect = ModelError("bad key", provider="openai", model="gpt-4o-mini")

    env["client"].post("/api/rag", json={"query": "widgets"}, headers=_auth(env["access"]))

    db = env["SessionLocal"]()
    row = db.query(env["PromptExecution"]).one()
    db.close()
    assert row.status == "failed"


def test_rag_requires_jwt(env):
    resp = env["client"].post("/api/rag", json={"query": "widgets"})
    assert resp.status_code == 401


def test_rag_query_too_short_returns_400(env, mocker):
    _mock_embed(mocker, [1.0])
    resp = env["client"].post("/api/rag", json={"query": "a"}, headers=_auth(env["access"]))
    assert resp.status_code == 400
