"""Tests for GET /api/documents/search and POST /api/rag — standalone
Flask app + in-memory SQLite (not server.py, avoids needing a live DB),
mocking ModelRegistry (embedding + generation) and PromptRegistry per
this task's own instruction. Chunk embeddings are real Python lists
scored with the module's own real _cosine(), not mocked — the point of
these tests is verifying the ranking/filtering logic actually works,
not just that a mock was called.

Run: pytest backend/search/test_search.py -v
"""
import json
from datetime import timedelta

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

from auth.jwt_utils import create_jwt
from backend.search.routes import create_search_blueprint
from backend.search import routes as search_routes
from backend.ai import ModelError


@pytest.fixture
def env():
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
        embedding = Column(Text)   # JSON list[float] | null
        page = Column(Integer, nullable=True)
        section = Column(String(200), nullable=True)

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    app.register_blueprint(create_search_blueprint(
        SessionLocal=SessionLocal, UserFile=UserFile, Chunk=Chunk, utility_model="gpt-4o-mini",
    ))

    with app.app_context():
        access, _ = create_jwt(1)

    return {
        "client": app.test_client(), "access": access, "SessionLocal": SessionLocal,
        "UserFile": UserFile, "Chunk": Chunk,
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _add_file_with_chunk(env, user_id=1, title="Widget Paper", content="Widgets are efficient.",
                         embedding=None, page=None, project_id=None):
    db = env["SessionLocal"]()
    uf = env["UserFile"](user_id=user_id, title=title, name=f"{title}.pdf",
                         kind="document", project_id=project_id)
    db.add(uf)
    db.flush()
    ch = env["Chunk"](file_id=uf.id, content=content,
                      embedding=json.dumps(embedding) if embedding is not None else None,
                      page=page)
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
        "content": "This is the answer.", "model": "gpt-4o-mini",
        "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
        "finish_reason": "stop", "cost": 0.001,
    }
    mocker.patch.object(search_routes, "ModelRegistry", return_value=model_registry)
    return model_registry


@pytest.fixture(autouse=True)
def fake_prompt_registry(mocker):
    prompt_registry = mocker.Mock()
    prompt_registry.get_prompt.return_value = "rendered rag prompt"
    mocker.patch.object(search_routes, "PromptRegistry", return_value=prompt_registry)
    mocker.patch.object(search_routes, "ensure_default_prompts")
    return prompt_registry


# ------------------------------------------------------------ GET /api/documents/search
def test_search_ranks_by_cosine_similarity(env, mocker):
    _add_file_with_chunk(env, title="Close match", content="widgets are great",
                         embedding=[1.0, 0.0, 0.0])
    _add_file_with_chunk(env, title="Far match", content="unrelated content",
                         embedding=[0.0, 1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0, 0.0])   # query vector identical to "Close match"

    resp = env["client"].get("/api/documents/search?q=widgets", headers=_auth(env["access"]))

    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert len(results) == 1   # "Far match" scores 0.0, below the 0.15 threshold
    assert results[0]["title"] == "Close match"
    assert results[0]["score"] == 1.0


def test_search_skips_chunks_without_embedding(env, mocker):
    _add_file_with_chunk(env, embedding=None)   # no embedding at all
    _mock_embed(mocker, [1.0, 0.0, 0.0])

    resp = env["client"].get("/api/documents/search?q=widgets", headers=_auth(env["access"]))

    assert resp.get_json()["results"] == []


def test_search_scopes_to_requesting_user(env, mocker):
    _add_file_with_chunk(env, user_id=2, embedding=[1.0, 0.0, 0.0])   # different user
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
    _add_file_with_chunk(env, title="Widget Paper", content="Widgets are efficient under low load.",
                         embedding=[1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0])

    resp = env["client"].post("/api/rag", json={"query": "are widgets efficient?"},
                              headers=_auth(env["access"]))

    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["answer"] == "This is the answer."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["title"] == "Widget Paper"


def test_rag_passes_documents_and_question_to_prompt(env, mocker, fake_prompt_registry):
    _add_file_with_chunk(env, title="Widget Paper", content="Widgets are efficient.",
                         embedding=[1.0, 0.0])
    _mock_embed(mocker, [1.0, 0.0])

    env["client"].post("/api/rag", json={"query": "are widgets efficient?"}, headers=_auth(env["access"]))

    fake_prompt_registry.get_prompt.assert_called_once()
    assert fake_prompt_registry.get_prompt.call_args[0][0] == "semantic_search"
    variables = fake_prompt_registry.get_prompt.call_args.kwargs["variables"]
    assert "Widgets are efficient." in variables["documents"]
    assert variables["question"] == "are widgets efficient?"


def test_rag_no_matching_documents_returns_empty_answer(env, mocker):
    _mock_embed(mocker, [1.0, 0.0])   # no chunks exist at all

    resp = env["client"].post("/api/rag", json={"query": "anything"}, headers=_auth(env["access"]))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["answer"] is None
    assert body["sources"] == []


def test_rag_model_error_returns_502(env, mocker):
    _add_file_with_chunk(env, embedding=[1.0, 0.0])
    model_registry = _mock_embed(mocker, [1.0, 0.0])
    model_registry.call.side_effect = ModelError("bad key", provider="openai", model="gpt-4o-mini")

    resp = env["client"].post("/api/rag", json={"query": "widgets"}, headers=_auth(env["access"]))
    assert resp.status_code == 502


def test_rag_requires_jwt(env):
    resp = env["client"].post("/api/rag", json={"query": "widgets"})
    assert resp.status_code == 401


def test_rag_query_too_short_returns_400(env, mocker):
    _mock_embed(mocker, [1.0])
    resp = env["client"].post("/api/rag", json={"query": "a"}, headers=_auth(env["access"]))
    assert resp.status_code == 400
