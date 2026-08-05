"""Integration tests for POST /api/documents/upload — a standalone Flask
app + in-memory SQLite (not server.py, avoids needing a live DB/R2), with
a mocked storage backend per the task's own instruction. QuotaService is
real (in-memory-backed), since exercising the actual 403 rejection path
is the point, not just asserting a mock was called.

Run: pytest backend/upload/test_upload.py -v
"""

import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from auth.jwt_utils import create_jwt
from backend.ai import ModelError
from backend.ai.domain_registry import DomainRegistry
from backend.ai.memory_engine import MemoryEngine
from backend.ai.model_router import ModelRouter
from backend.ai.persona_engine import PersonaEngine
from backend.ai.prompt_builder import PromptBuilder
from backend.ai.prompt_registry import Persona, PromptExecution, PromptRegistry
from backend.ai.prompt_registry import _Base as prompt_engine_base
from backend.ai.system_prompt import SystemPromptManager
from backend.upload import routes as upload_routes
from backend.upload.routes import create_documents_blueprint
from backend.upload.validation import ValidationError, validate_extension, validate_size
from quotas.models import create_usage_log_model
from quotas.service import QuotaService


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
        storage_limit_bytes = Column(BigInteger, default=QuotaService.DEFAULT_STORAGE_LIMIT_BYTES)
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
        project_id = Column(Integer, nullable=True)
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

    # Real PromptExecution (backend.ai.prompt_registry), not a test-local
    # stand-in: it carries real ForeignKeys to prompt_versions/personas,
    # which only resolve if it's the same class registered against that
    # module's own _Base (see prompt_registry.py's own docstring on why
    # PromptExecution lives there rather than getting redefined per test).
    #
    # Memory/Project are test-local: PromptBuilder needs *some* mapped
    # classes for those slots, but nothing here exercises memory
    # relevance or project context (no project_id/user memories are set
    # up in these tests), so minimal stand-ins are enough.
    class Memory(Base):
        __tablename__ = "memories"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        project_id = Column(Integer, nullable=True)
        fact = Column(String, nullable=False)
        importance = Column(Integer, default=3)
        created_at = Column(DateTime, nullable=True)

    class Project(Base):
        __tablename__ = "projects"
        id = Column(Integer, primary_key=True)
        description = Column(String, default="")
        instructions = Column(String, default="")

    UsageLog = create_usage_log_model(Base)
    Base.metadata.create_all(engine)
    prompt_engine_base.metadata.create_all(engine)  # prompt_versions, personas, prompt_executions
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    db = SessionLocal()
    db.add(User(id=1))
    db.commit()
    # A real, active system prompt — PromptBuilder.build() fetches this
    # unconditionally; leaving it unseeded would 400 every single request
    # here on a ValueError that has nothing to do with what's under test.
    SystemPromptManager(PromptRegistry(db)).set_active_prompt("You are a helpful research assistant.")
    db.close()

    quota_service = QuotaService(SessionLocal, User, StorageUsage, UsageLog, select)
    storage_backend = FakeStorageBackend()

    def get_prompt_builder(db_session):
        """Mirrors server.py's own get_prompt_builder(db_session) factory
        exactly (same constructor args, same "one real PromptBuilder per
        request" shape) — the whole point of these tests is exercising
        the real Prompt Engine wiring, not a mock standing in for it."""
        registry = PromptRegistry(db_session)
        return PromptBuilder(
            system_prompt_manager=SystemPromptManager(registry),
            persona_engine=PersonaEngine(db_session, Persona),
            memory_engine=MemoryEngine(db_session, Memory),
            prompt_registry=registry,
            SessionLocal=SessionLocal,
            Project=Project,
            domain_registry=DomainRegistry(),
        )

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    model_router = ModelRouter(defaults={"paper_analysis": "gpt-4o-mini", "_default": "gpt-4o-mini"})
    app.register_blueprint(
        create_documents_blueprint(
            SessionLocal=SessionLocal,
            UserFile=UserFile,
            UploadBatch=UploadBatch,
            UploadJob=UploadJob,
            OutboxEvent=OutboxEvent,
            PaperAnalysis=PaperAnalysis,
            PromptExecution=PromptExecution,
            quota_service=quota_service,
            storage_backend=storage_backend,
            model_router=model_router,
            get_prompt_builder=get_prompt_builder,
            domain_registry=DomainRegistry(),
        )
    )

    with app.app_context():
        access, _ = create_jwt(1)

    return {
        "client": app.test_client(),
        "access": access,
        "SessionLocal": SessionLocal,
        "User": User,
        "StorageUsage": StorageUsage,
        "UserFile": UserFile,
        "UploadJob": UploadJob,
        "OutboxEvent": OutboxEvent,
        "PaperAnalysis": PaperAnalysis,
        "PromptExecution": PromptExecution,
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
    job = db.execute(select(env["UploadJob"]).where(env["UploadJob"].file_id == doc_id)).scalar_one()
    event = db.execute(select(env["OutboxEvent"]).where(env["OutboxEvent"].aggregate_id == job.id)).scalar_one()
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
    _upload(env["client"], env["access"], filename="notes.txt", content=b"12345")
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


def test_rejects_mismatched_magic_bytes(env):
    # Extension claims PDF but payload is plain text
    resp = _upload(env["client"], env["access"], filename="paper.pdf", content=b"not a pdf")
    assert resp.status_code == 400, resp.get_json()
    assert resp.get_json()["error"] == "invalid_mime"
    assert not env["storage_backend"].uploaded


def test_validate_extension_allows_all_four_spec_types():
    for name in ("paper.pdf", "book.epub", "report.docx", "notes.txt"):
        validate_extension(name)  # no raise


# ------------------------------------------------------------ quota
def test_quota_exceeded_returns_403_and_never_touches_storage(env):
    db = env["SessionLocal"]()
    db.add(env["StorageUsage"](user_id=1, bytes_used=999_999_990, file_count=1))
    db.commit()
    db.close()

    resp = _upload(env["client"], env["access"], filename="notes.txt", content=b"x" * 100)
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
        user_id=1,
        name="paper.pdf",
        mime="application/pdf",
        kind="document",
        path="fake/key.pdf",
        size=100,
        title=title,
        authors=authors,
        abstract=abstract,
    )
    db.add(uf)
    db.commit()
    doc_id = uf.id
    db.close()
    return doc_id


_ANALYSIS_JSON = {
    "executive_summary": "A summary.",
    "abstract_explained": "x",
    "research_objective": "x",
    "problem_statement": "x",
    "methodology": "x",
    "dataset": None,
    "experiments": "x",
    "results": "x",
    "key_contributions": ["a"],
    "strengths": ["b"],
    "limitations": ["c"],
    "future_work": ["d"],
    "keywords": ["e"],
    "important_terms": [{"term": "x", "definition": "y"}],
}


def _mock_model_registry(mocker, response_json=None, model_side_effect=None):
    """Only ModelRegistry is mocked (the external-network boundary) —
    PromptRegistry/PromptBuilder run for real against env's in-memory DB
    (see get_prompt_builder in the env fixture), matching this app's
    "real classes over mocks for pure-orchestration logic" convention
    (backend/ai/test_*.py) rather than re-mocking prompt assembly here."""
    model_registry = mocker.Mock()
    if model_side_effect:
        model_registry.call.side_effect = model_side_effect
    else:
        model_registry.call.return_value = {
            "content": json.dumps(response_json or _ANALYSIS_JSON),
            "model": "gpt-4o-mini",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "finish_reason": "stop",
            "cost": 0.001,
        }
    mocker.patch.object(upload_routes, "ModelRegistry", return_value=model_registry)
    return model_registry


def _sent_prompt(model_registry):
    """The exact string sent as the model's user-role message content —
    i.e. PromptBuilder's assembled.final, whatever it ended up being."""
    return model_registry.call.call_args[0][1][0]["content"]


def _seed_domain_module(env, name, template):
    db = env["SessionLocal"]()
    PromptRegistry(db).create_prompt(name, "test domain module", template, status="active")
    db.close()


def _active_paper_analysis_version_id(env):
    """The real id of whichever "paper_analysis" version ensure_default_prompts()
    seeded — id=3 in this fixture's setup order (system_prompt=1,
    extract_metadata=2, paper_analysis=3) but derived here, not
    hardcoded, so it isn't silently wrong if that setup order ever
    changes."""
    db = env["SessionLocal"]()
    version_id = PromptRegistry(db).get_active_version("paper_analysis").id
    db.close()
    return version_id


@pytest.fixture(autouse=True)
def fake_extract_text(mocker):
    mocker.patch.object(upload_routes, "extract_text", return_value="Extracted paper body text.")


def test_analyze_document_calls_model_registry_with_the_assembled_prompt(env, mocker):
    doc_id = _sample_document(env)
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert resp.status_code == 200, resp.get_json()
    model_registry.call.assert_called_once()
    assert model_registry.call.call_args.kwargs["user_id"] == 1
    # A real Structured Outputs schema, not plain {"type": "json_object"}
    # mode — see backend/ai/prompts.py's PAPER_ANALYSIS_RESPONSE_FORMAT
    # comment for why that distinction matters (json_object mode doesn't
    # actually guarantee the model uses these field names).
    response_format = model_registry.call.call_args.kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "paper_analysis"
    assert response_format["json_schema"]["strict"] is True
    # The real, currently-active production paper_analysis template
    # (backend/ai/prompts.py) — proves this route now assembles through
    # the real PromptRegistry/PromptBuilder, not a stubbed-out one.
    assert "Analyse the paper below" in _sent_prompt(model_registry)
    assert "Extracted paper body text." in _sent_prompt(model_registry)


def test_analyze_document_composes_title_authors_abstract_into_text(env, mocker):
    doc_id = _sample_document(env, title="My Paper", authors="A. Author", abstract="An abstract.")
    model_registry = _mock_model_registry(mocker)

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    sent = _sent_prompt(model_registry)
    assert "Title: My Paper" in sent
    assert "Authors: A. Author" in sent
    assert "Extracted paper body text." in sent


def test_analyze_document_writes_paper_analysis_row(env, mocker):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker, response_json={**_ANALYSIS_JSON, "executive_summary": "Great paper."})

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    db = env["SessionLocal"]()
    pa = db.execute(select(env["PaperAnalysis"]).where(env["PaperAnalysis"].file_id == doc_id)).scalar_one()
    db.close()
    assert pa.status == "done"
    assert pa.model == "gpt-4o-mini"
    data = json.loads(pa.data)
    assert data["executive_summary"] == "Great paper."


def test_analyze_document_returns_analysis_json_and_prompt_metadata(env, mocker):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    body = resp.get_json()
    assert body["document_id"] == doc_id
    assert body["analysis"]["executive_summary"] == "A summary."
    assert body["domain_detected"] == "general"  # no domain-specific keywords in the fake extracted text
    assert body["domain_used"] == "general"
    assert body["domain_version_id"] is None  # "general" reuses paper_analysis itself, no separate module
    assert isinstance(body["sections_count"], int) and body["sections_count"] > 0
    assert body["prompt_version_id"] == _active_paper_analysis_version_id(env)


def test_analyze_document_normalizes_string_array_fields(env, mocker):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker, response_json={**_ANALYSIS_JSON, "keywords": "single-keyword"})

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert resp.get_json()["analysis"]["keywords"] == ["single-keyword"]


def test_analyze_document_not_found_for_missing_document(env, mocker):
    _mock_model_registry(mocker)
    resp = env["client"].post("/api/documents/999999/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 404


def test_analyze_document_not_found_for_other_users_document(env, mocker):
    db = env["SessionLocal"]()
    uf = env["UserFile"](user_id=2, name="other.pdf", mime="application/pdf", kind="document", path="k", size=1)
    db.add(uf)
    db.commit()
    doc_id = uf.id
    db.close()
    _mock_model_registry(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 404


def test_analyze_document_no_extractable_text_returns_422(env, mocker):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker)
    mocker.patch.object(upload_routes, "extract_text", return_value="")

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))
    assert resp.status_code == 422


def test_analyze_document_model_error_returns_500_and_logs(env, mocker, caplog):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker, model_side_effect=ModelError("bad key", provider="openai", model="gpt-4o-mini"))

    with caplog.at_level("ERROR"):
        resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert resp.status_code == 500
    assert any("model call failed" in r.message for r in caplog.records)


def test_analyze_document_requires_jwt(env):
    resp = env["client"].post("/api/documents/1/analysis")
    assert resp.status_code == 401


def test_analyze_document_writes_successful_prompt_execution_row(env, mocker):
    doc_id = _sample_document(env)
    model_registry = _mock_model_registry(mocker)

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    db = env["SessionLocal"]()
    row = db.query(env["PromptExecution"]).one()
    db.close()
    assert row.status == "success"
    assert row.prompt_version_id == _active_paper_analysis_version_id(env)
    assert row.user_id == 1
    assert row.assembled_prompt == _sent_prompt(model_registry)
    assert row.tokens_used == 15


def test_analyze_document_model_error_marks_prompt_execution_failed(env, mocker):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker, model_side_effect=ModelError("bad key", provider="openai", model="gpt-4o-mini"))

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    db = env["SessionLocal"]()
    row = db.query(env["PromptExecution"]).one()
    db.close()
    assert row.status == "failed"


def test_analyze_document_calls_model_registry_with_prompt_version_id(env, mocker):
    doc_id = _sample_document(env)
    model_registry = _mock_model_registry(mocker)

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert model_registry.call.call_args.kwargs["prompt_version_id"] == _active_paper_analysis_version_id(env)


# ------------------------------------------------------------ domain / metadata / user_query
def test_analyze_document_with_medical_domain(env, mocker):
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "## 17. PICO Extraction\n{{ text }}")
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "medical"},
        headers=_auth(env["access"]),
    )

    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["domain_used"] == "medical"
    assert body["domain_version_id"] is not None
    assert "## 17. PICO Extraction" in _sent_prompt(model_registry)


def test_analyze_document_uses_medical_core_response_format_when_document_type_unrecognized(env, mocker):
    # _sample_document's extracted text ("Extracted paper body text.") has
    # no research/clinical_guide/review keywords, so document_type
    # auto-detects to "general" — the medical schema should still apply
    # (domain=medical was explicitly requested) but with only the 3
    # always-on core fields, none of the document-type-specific ones.
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "MEDICAL: {{ text }}")
    model_registry = _mock_model_registry(mocker)

    env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "medical"},
        headers=_auth(env["access"]),
    )

    response_format = model_registry.call.call_args.kwargs["response_format"]
    assert response_format["json_schema"]["name"] == "paper_analysis_medical"
    props = response_format["json_schema"]["schema"]["properties"]
    assert "clinical_relevance" in props
    assert "clinical_translation" in props
    assert "clinical_bottom_line" in props
    # Base fields are still required too — a medical-domain analysis
    # extends the core schema, it doesn't replace it.
    assert "executive_summary" in props
    # No document-type-specific fields from any variant.
    assert "pico_extraction" not in props
    assert "target_audience" not in props
    assert "review_coverage" not in props


def test_analyze_document_medical_research_document_type_adds_research_fields(env, mocker):
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "MEDICAL: {{ text }}")
    mocker.patch.object(
        upload_routes,
        "extract_text",
        return_value="This randomized controlled trial enrolled a cohort of patients.",
    )
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "medical"},
        headers=_auth(env["access"]),
    )

    body = resp.get_json()
    assert body["document_type"] == "research"
    response_format = model_registry.call.call_args.kwargs["response_format"]
    props = response_format["json_schema"]["schema"]["properties"]
    assert "pico_extraction" in props
    assert "grade_assessment" in props
    assert "target_audience" not in props
    assert "review_coverage" not in props


def test_analyze_document_medical_clinical_guide_document_type_adds_guide_fields(env, mocker):
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "MEDICAL: {{ text }}")
    mocker.patch.object(
        upload_routes,
        "extract_text",
        return_value="This practical guide explains step by step how to perform the procedure.",
    )
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "medical"},
        headers=_auth(env["access"]),
    )

    body = resp.get_json()
    assert body["document_type"] == "clinical_guide"
    response_format = model_registry.call.call_args.kwargs["response_format"]
    props = response_format["json_schema"]["schema"]["properties"]
    assert "target_audience" in props
    assert "comparison_to_other_resources" in props
    assert "pico_extraction" not in props
    assert "review_coverage" not in props


def test_analyze_document_medical_review_document_type_adds_review_fields(env, mocker):
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "MEDICAL: {{ text }}")
    mocker.patch.object(
        upload_routes,
        "extract_text",
        return_value="We performed a systematic review and meta-analysis of the literature.",
    )
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "medical"},
        headers=_auth(env["access"]),
    )

    body = resp.get_json()
    assert body["document_type"] == "review"
    response_format = model_registry.call.call_args.kwargs["response_format"]
    props = response_format["json_schema"]["schema"]["properties"]
    assert "review_coverage" in props
    assert "future_research_directions" in props
    assert "pico_extraction" not in props
    assert "target_audience" not in props


def test_analyze_document_domain_medical_template_reflects_document_type(env, mocker):
    # The real, seeded domain_medical content (backend/ai/seed.py's
    # DOMAIN_MODULES, not a test-faked stand-in) — proves the actual
    # {% if document_type == ... %} branch renders correctly, not just
    # that the schema was picked correctly.
    from backend.ai.seed import DOMAIN_MODULES

    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", DOMAIN_MODULES["domain_medical"])
    mocker.patch.object(
        upload_routes,
        "extract_text",
        return_value="This randomized controlled trial enrolled a cohort of patients.",
    )
    model_registry = _mock_model_registry(mocker)

    env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "medical"},
        headers=_auth(env["access"]),
    )

    sent = _sent_prompt(model_registry)
    assert "This document appears to be a research." in sent
    assert "PICO extraction" in sent
    assert "Target audience" not in sent


def test_analyze_document_uses_base_response_format_for_general_domain(env, mocker):
    doc_id = _sample_document(env)
    model_registry = _mock_model_registry(mocker)

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    response_format = model_registry.call.call_args.kwargs["response_format"]
    assert response_format["json_schema"]["name"] == "paper_analysis"
    assert "pico_extraction" not in response_format["json_schema"]["schema"]["properties"]


def test_analyze_document_with_auto_detect(env, mocker):
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "## 17. PICO Extraction\n{{ text }}")
    mocker.patch.object(
        upload_routes,
        "extract_text",
        return_value="This randomized clinical trial enrolled patients at a hospital.",
    )
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["domain_detected"] == "medical"
    assert body["domain_used"] == "medical"
    assert "## 17. PICO Extraction" in _sent_prompt(model_registry)


def test_analyze_document_with_domain_override_beats_auto_detect(env, mocker):
    # Content reads medical, but an explicit override still wins —
    # matches DomainRegistry.detect_domain()'s own priority order
    # (already covered at the unit level in test_prompt_builder.py; this
    # just proves the route actually forwards the override instead of
    # always letting detection decide).
    doc_id = _sample_document(env)
    _seed_domain_module(env, "domain_medical", "MEDICAL: {{ text }}")
    _seed_domain_module(env, "domain_ai_ml", "AI_ML: {{ text }}")
    mocker.patch.object(upload_routes, "extract_text", return_value="a randomized clinical trial")
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "ai_ml"},
        headers=_auth(env["access"]),
    )

    body = resp.get_json()
    assert body["domain_detected"] == "medical"  # what auto-detection alone would have picked
    assert body["domain_used"] == "ai_ml"  # what was actually applied — the override
    assert "AI_ML:" in _sent_prompt(model_registry)
    assert "MEDICAL:" not in _sent_prompt(model_registry)


def test_analyze_document_with_custom_user_query(env, mocker):
    # The currently-active production paper_analysis template
    # (backend/ai/prompts.py) doesn't reference {{ query }} at all, so a
    # custom question can't be observed through it — this test swaps in
    # a controlled template that does, to prove the route actually
    # threads user_query into PromptBuilder.build() rather than
    # hardcoding "Analyze this paper".
    mocker.patch.object(upload_routes, "ensure_default_prompts")  # don't let it reset this back
    doc_id = _sample_document(env)
    db = env["SessionLocal"]()
    PromptRegistry(db).create_prompt("paper_analysis", "test", "Q: {{ query }} | DOC: {{ text }}", status="active")
    db.close()
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"user_query": "What are the ethical implications?"},
        headers=_auth(env["access"]),
    )

    assert resp.status_code == 200, resp.get_json()
    assert "Q: What are the ethical implications?" in _sent_prompt(model_registry)


def test_analyze_document_default_user_query_when_not_supplied(env, mocker):
    mocker.patch.object(upload_routes, "ensure_default_prompts")
    doc_id = _sample_document(env)
    db = env["SessionLocal"]()
    PromptRegistry(db).create_prompt("paper_analysis", "test", "Q: {{ query }}", status="active")
    db.close()
    model_registry = _mock_model_registry(mocker)

    env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert "Q: Analyze this paper" in _sent_prompt(model_registry)


def test_analyze_document_invalid_domain_returns_400(env, mocker):
    doc_id = _sample_document(env)
    _mock_model_registry(mocker)

    resp = env["client"].post(
        f"/api/documents/{doc_id}/analysis",
        json={"domain": "astrology"},
        headers=_auth(env["access"]),
    )

    body = resp.get_json()
    assert resp.status_code == 400
    assert body["error"] == "invalid_domain"


def test_analyze_document_not_ready_returns_409_and_skips_model_call(env, mocker):
    doc_id = _sample_document(env)
    db = env["SessionLocal"]()
    db.add(env["UploadJob"](file_id=doc_id, user_id=1, job_type="import", status="running"))
    db.commit()
    db.close()
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    body = resp.get_json()
    assert resp.status_code == 409
    assert body["message"] == "Document content not yet extracted. Please wait."
    model_registry.call.assert_not_called()


def test_analyze_document_token_quota_exceeded_returns_403(env, mocker, monkeypatch):
    # QuotaService.check_token_quota() falls back to DEFAULT_TOKEN_LIMIT
    # via `or` whenever monthly_token_limit is falsy (0 included) — so
    # exceeding it means pushing monthly_token_used near the *default*,
    # not setting the limit column to 0 (same convention the existing
    # storage-quota test above already uses for the analogous case).
    # quota_reset_at must be set into the future too: _ensure_reset()
    # treats a never-initialized reset_at as "start a fresh window now"
    # and would zero monthly_token_used right before the check otherwise
    # (see quotas/test_service.py's identical setup for this exact trap).
    monkeypatch.setenv("DHUND_SUSPEND_AI_QUOTAS", "0")
    doc_id = _sample_document(env)
    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    user.monthly_token_used = QuotaService.DEFAULT_TOKEN_LIMIT - 1
    user.quota_reset_at = datetime.now(timezone.utc) + timedelta(days=15)
    db.commit()
    db.close()
    model_registry = _mock_model_registry(mocker)

    resp = env["client"].post(f"/api/documents/{doc_id}/analysis", headers=_auth(env["access"]))

    assert resp.status_code == 403
    assert resp.get_json()["error"] == "token_quota_exceeded"
    model_registry.call.assert_not_called()
