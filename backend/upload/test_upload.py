"""Integration tests for POST /api/documents/upload — a standalone Flask
app + in-memory SQLite (not server.py, avoids needing a live DB/R2), with
a mocked storage backend per the task's own instruction. QuotaService is
real (in-memory-backed), since exercising the actual 403 rejection path
is the point, not just asserting a mock was called.

Run: pytest backend/upload/test_upload.py -v
"""

import io
import json
from datetime import timedelta

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from auth.jwt_utils import create_jwt
from quotas.service import QuotaService
from quotas.models import create_usage_log_model
from backend.upload import routes as upload_routes
from backend.upload.routes import create_documents_blueprint
from backend.ai import ModelError
from backend.upload.validation import validate_size, validate_extension, ValidationError


class FakeStorageBackend:
    """Records calls instead of touching R2/disk."""

    def __init__(self, fail=False):
        self.fail = fail
        self.uploaded = []  # (key, content_type, bytes)
        self.deleted = []

    def upload(self, file_obj, key, content_type=None):
        if self.fail:
            raise RuntimeError("simulated storage failure")
        self.uploaded.append((key, content_type, file_obj.read()))
        return key

    def download(self, key):
        if self.fail:
            raise RuntimeError("simulated storage failure")
        return b"fake stored bytes"

    def delete(self, key):
        self.deleted.append(key)


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        storage_limit_bytes = Column(
            BigInteger, default=QuotaService.DEFAULT_STORAGE_LIMIT_BYTES
        )
        monthly_token_used = Column(Integer, default=0)
        monthly_token_limit = Column(Integer, default=QuotaService.DEFAULT_TOKEN_LIMIT)
        quota_reset_at = Column(DateTime, nullable=True)

    class StorageUsage(Base):
        __tablename__ = "storage_usage"
        user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
        bytes_used = Column(Integer, default=0)
        file_count = Column(Integer, default=0)

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        name = Column(String(300))
        mime = Column(String(120))
        kind = Column(String(20))
        path = Column(String(500))
        size = Column(Integer)
        title = Column(String(500))
        authors = Column(String(1000))
        abstract = Column(String)

    class UploadBatch(Base):
        __tablename__ = "upload_batches"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        source = Column(String(20))
        file_count = Column(Integer, default=0)

    class UploadJob(Base):
        __tablename__ = "upload_jobs"
        id = Column(Integer, primary_key=True)
        upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"))
        file_id = Column(Integer, ForeignKey("files.id"))
        user_id = Column(Integer, ForeignKey("users.id"))
        job_type = Column(String(30))
        status = Column(String(20), default="pending")

    class OutboxEvent(Base):
        __tablename__ = "outbox_events"
        id = Column(Integer, primary_key=True)
        aggregate_type = Column(String(30))
        aggregate_id = Column(Integer)
        event_type = Column(String(50))
        payload = Column(String(2000))
        status = Column(String(20), default="pending")

    class PaperAnalysis(Base):
        __tablename__ = "paper_analyses"
        id = Column(Integer, primary_key=True)
        file_id = Column(Integer, ForeignKey("files.id"), unique=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        status = Column(String(20), default="pending")
        error = Column(String(500), default="")
        content_hash = Column(String(64), default="")
        model = Column(String(100), default="")
        data = Column(String, default="")

    UsageLog = create_usage_log_model(Base)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    db = SessionLocal()
    db.add(User(id=1))
    db.commit()
    db.close()

    quota_service = QuotaService(SessionLocal, User, StorageUsage, UsageLog, select)
    storage_backend = FakeStorageBackend()

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    app.register_blueprint(
        create_documents_blueprint(
            SessionLocal=SessionLocal,
            UserFile=UserFile,
            UploadBatch=UploadBatch,
            UploadJob=UploadJob,
            OutboxEvent=OutboxEvent,
            PaperAnalysis=PaperAnalysis,
            quota_service=quota_service,
            storage_backend=storage_backend,
            utility_model="gpt-4o-mini",
        )
    )

    with app.app_context():
        access, _ = create_jwt(1)

    return {
        "client": app.test_client(),
        "access": access,
        "SessionLocal": SessionLocal,
        "StorageUsage": StorageUsage,
        "UserFile": UserFile,
        "UploadJob": UploadJob,
        "OutboxEvent": OutboxEvent,
        "PaperAnalysis": PaperAnalysis,
        "storage_backend": storage_backend,
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _upload(client, token, filename="paper.pdf", content=b"%PDF-1.4 fake pdf bytes"):
    data = {"file": (io.BytesIO(content), filename)}
    return client.post(
        "/api/documents/upload",
        data=data,
        headers=_auth(token),
        content_type="multipart/form-data",
    )


# ------------------------------------------------------------ success path
def test_successful_upload_returns_pending_document(env):
    resp = _upload(env["client"], env["access"])
    body = resp.get_json()
    assert resp.status_code == 201, body
    assert body["status"] == "PENDING"
    assert isinstance(body["document_id"], int)
    assert "processing started" in body["message"].lower()


def test_successful_upload_writes_file_row_and_enqueues_job(env):
    resp = _upload(env["client"], env["access"])
    doc_id = resp.get_json()["document_id"]

    db = env["SessionLocal"]()
    uf = db.get(env["UserFile"], doc_id)
    job = db.execute(
        select(env["UploadJob"]).where(env["UploadJob"].file_id == doc_id)
    ).scalar_one()
    event = db.execute(
        select(env["OutboxEvent"]).where(env["OutboxEvent"].aggregate_id == job.id)
    ).scalar_one()
    db.close()

    assert uf.name == "paper.pdf"
    assert uf.user_id == 1
    assert job.job_type == "import"
    assert job.status == "pending"
    assert event.event_type == "job.enqueued"


def test_successful_upload_calls_storage_backend_with_scoped_key(env):
    _upload(env["client"], env["access"], filename="notes.txt", content=b"hello")
    assert len(env["storage_backend"].uploaded) == 1
    key, content_type, data = env["storage_backend"].uploaded[0]
    assert key.startswith("users/1/documents/")
    assert key.endswith("notes.txt")
    assert data == b"hello"


def test_successful_upload_updates_storage_usage_counter(env):
    _upload(env["client"], env["access"], content=b"12345")
    db = env["SessionLocal"]()
    usage = db.get(env["StorageUsage"], 1)
    db.close()
    assert usage.bytes_used == 5
    assert usage.file_count == 1


# ------------------------------------------------------------ validation
def test_rejects_unsupported_extension(env):
    resp = _upload(env["client"], env["access"], filename="malware.exe")
    assert resp.status_code == 400, resp.get_json()
    assert resp.get_json()["error"] == "unsupported_type"
    assert not env["storage_backend"].uploaded


def test_rejects_empty_file(env):
    resp = _upload(env["client"], env["access"], content=b"")
    assert resp.status_code == 400, resp.get_json()
    assert resp.get_json()["error"] == "empty_file"


def test_no_file_in_request(env):
    resp = env["client"].post(
        "/api/documents/upload",
        headers=_auth(env["access"]),
        content_type="multipart/form-data",
        data={},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_file"


def test_requires_jwt(env):
    resp = env["client"].post(
        "/api/documents/upload",
        data={"file": (io.BytesIO(b"x"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_validate_size_rejects_over_limit():
    with pytest.raises(ValidationError) as exc:
        validate_size(2 * 1024 * 1024, max_mb=1)
    assert exc.value.code == "too_large"


def test_validate_extension_allows_all_four_spec_types():
    for name in ("paper.pdf", "book.epub", "report.docx", "notes.txt"):
        validate_extension(name)  # no raise


# ------------------------------------------------------------ quota
def test_quota_exceeded_returns_403_and_never_touches_storage(env):
    db = env["SessionLocal"]()
    db.add(env["StorageUsage"](user_id=1, bytes_used=999_999_990, file_count=1))
    db.commit()
    db.close()

    resp = _upload(env["client"], env["access"], content=b"x" * 100)
    body = resp.get_json()
    assert resp.status_code == 403, body
    assert body["error"] == "storage_quota_exceeded"
    assert not env["storage_backend"].uploaded


# ------------------------------------------------------------ storage failure
def test_storage_failure_returns_502_and_writes_no_file_row(env):
    env["storage_backend"].fail = True
    resp = _upload(env["client"], env["access"])
    assert resp.status_code == 502, resp.get_json()

    db = env["SessionLocal"]()
    count = len(db.execute(select(env["UserFile"])).scalars().all())
    db.close()
    assert count == 0


# ------------------------------------------------------------ POST /<id>/analysis
def _sample_document(env, title=None, authors=None, abstract=None):
    db = env["SessionLocal"]()
    uf = env["UserFile"](
        user_id=1, name="paper.pdf", mime="application/pdf", kind="document",
        path="fake/key.pdf", size=100, title=title, authors=authors, abstract=abstract,
    )
    db.add(uf)
    db.commit()
    doc_id = uf.id
    db.close()
    return doc_id


_ANALYSIS_JSON = {
    "executive_summary": "A summary.", "abstract_explained": "x", "research_objective": "x",
    "problem_statement": "x", "methodology": "x", "dataset": None, "experiments": "x",
    "results": "x", "key_contributions": ["a"], "strengths": ["b"], "limitations": ["c"],
    "future_work": ["d"], "keywords": ["e"], "important_terms": {"x": "y"},
}


def _mock_analysis_registries(mocker, response_json=None, model_side_effect=None):
    prompt_registry = mocker.Mock()
    prompt_registry.get_prompt.return_value = "rendered prompt"
    model_registry = mocker.Mock()
    if model_side_effect:
        model_registry.call.side_effect = model_side_effect
    else:
        model_registry.call.return_value = {
            "content": json.dumps(response_json or _ANALYSIS_JSON), "model": "gpt-4o-mini",
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
            "finish_reason": "stop", "cost": 0.001,
        }
    mocker.patch.object(upload_routes, "PromptRegistry", return_value=prompt_registry)
    mocker.patch.object(upload_routes, "ModelRegistry", return_value=model_registry)
    mocker.patch.object(upload_routes, "ensure_default_prompts")
    return prompt_registry, model_registry


@pytest.fixture(autouse=True)
def fake_extract_text(mocker):
    mocker.patch.object(upload_routes, "extract_text", return_value="Extracted paper body text.")


def test_analyze_document_calls_prompt_registry_and_model_registry(env, mocker):
    doc_id = _sample_document(env)
    prompt_registry, model_registry = _mock_analysis_registries(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert resp.status_code == 200, resp.get_json()
    prompt_registry.get_prompt.assert_called_once()
    assert prompt_registry.get_prompt.call_args[0][0] == "paper_analysis"
    model_registry.call.assert_called_once()
    assert model_registry.call.call_args.kwargs["user_id"] == 1
    assert model_registry.call.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_analyze_document_composes_title_authors_abstract_into_text(env, mocker):
    doc_id = _sample_document(env, title="My Paper", authors="A. Author", abstract="An abstract.")
    prompt_registry, _ = _mock_analysis_registries(mocker)

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    variables = prompt_registry.get_prompt.call_args.kwargs["variables"]
    assert "Title: My Paper" in variables["text"]
    assert "Authors: A. Author" in variables["text"]
    assert "Extracted paper body text." in variables["text"]


def test_analyze_document_writes_paper_analysis_row(env, mocker):
    doc_id = _sample_document(env)
    _mock_analysis_registries(mocker, response_json={**_ANALYSIS_JSON, "executive_summary": "Great paper."})

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    db = env["SessionLocal"]()
    pa = db.execute(
        select(env["PaperAnalysis"]).where(env["PaperAnalysis"].file_id == doc_id)
    ).scalar_one()
    db.close()
    assert pa.status == "done"
    assert pa.model == "gpt-4o-mini"
    data = json.loads(pa.data)
    assert data["executive_summary"] == "Great paper."


def test_analyze_document_returns_analysis_json(env, mocker):
    doc_id = _sample_document(env)
    _mock_analysis_registries(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    body = resp.get_json()
    assert body["document_id"] == doc_id
    assert body["status"] == "done"
    assert body["analysis"]["executive_summary"] == "A summary."


def test_analyze_document_normalizes_string_array_fields(env, mocker):
    doc_id = _sample_document(env)
    _mock_analysis_registries(mocker, response_json={**_ANALYSIS_JSON, "keywords": "single-keyword"})

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert resp.get_json()["analysis"]["keywords"] == ["single-keyword"]


def test_analyze_document_not_found_for_missing_document(env, mocker):
    _mock_analysis_registries(mocker)
    resp = env["client"].post("/api/documents/999999/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 404


def test_analyze_document_not_found_for_other_users_document(env, mocker):
    db = env["SessionLocal"]()
    uf = env["UserFile"](user_id=2, name="other.pdf", mime="application/pdf",
                         kind="document", path="k", size=1)
    db.add(uf)
    db.commit()
    doc_id = uf.id
    db.close()
    _mock_analysis_registries(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 404


def test_analyze_document_no_extractable_text_returns_422(env, mocker):
    doc_id = _sample_document(env)
    _mock_analysis_registries(mocker)
    mocker.patch.object(upload_routes, "extract_text", return_value="")

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 422


def test_analyze_document_model_error_returns_502(env, mocker):
    doc_id = _sample_document(env)
    _mock_analysis_registries(
        mocker, model_side_effect=ModelError("bad key", provider="openai", model="gpt-4o-mini"))

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 502


def test_analyze_document_requires_jwt(env):
    resp = env["client"].post("/api/documents/1/analysis")
    assert resp.status_code == 401
