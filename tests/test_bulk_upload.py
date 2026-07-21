"""Unit-style tests for POST /api/uploads/bulk and GET
/api/uploads/batch/<id>/status. Complements backend/upload/test_bulk.py
(which uses a hand-written fake storage backend + a real QuotaService
to exercise actual quota math) with the opposite layer: storage_backend
and QuotaService are both pytest-mock Mocks here, so these tests assert
on the route's own request/response handling in isolation.

tests/conftest.py's own `client` fixture is dead scaffolding — it scans
for app.py/run.py/main.py/wsgi.py, none of which exist in this repo
(entry point is server.py; see brain.md §10). This file defines its own
`client` fixture, which — same-name fixture in the test module itself —
takes priority over conftest.py's for every test here.

Run: pytest tests/test_bulk_upload.py -v
"""

import io
from datetime import timedelta

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from auth.jwt_utils import create_jwt
from quotas.service import QuotaExceededError
from backend.upload.bulk import create_bulk_upload_blueprint, MAX_BATCH_SIZE
from backend.upload.validation import ValidationError


@pytest.fixture
def db_models():
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        name = Column(String(300))
        mime = Column(String(120))
        kind = Column(String(20))
        path = Column(String(500))
        size = Column(Integer)

    class UploadBatch(Base):
        __tablename__ = "upload_batches"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        source = Column(String(20))
        file_count = Column(Integer, default=0)
        created_at = Column(DateTime)

    class UploadJob(Base):
        __tablename__ = "upload_jobs"
        id = Column(Integer, primary_key=True)
        upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"))
        file_id = Column(Integer, ForeignKey("files.id"))
        user_id = Column(Integer)
        job_type = Column(String(30))
        status = Column(String(20), default="pending")
        last_error = Column(String(500), nullable=True)

    class OutboxEvent(Base):
        __tablename__ = "outbox_events"
        id = Column(Integer, primary_key=True)
        aggregate_type = Column(String(30))
        aggregate_id = Column(Integer)
        event_type = Column(String(50))
        payload = Column(String(2000))

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return {
        "SessionLocal": SessionLocal,
        "UserFile": UserFile,
        "UploadBatch": UploadBatch,
        "UploadJob": UploadJob,
        "OutboxEvent": OutboxEvent,
    }


@pytest.fixture
def client(db_models, mocker):
    """storage_backend stands in for what get_storage_backend() would
    return; quota_service stands in for QuotaService — both mocked per
    the task brief, wired through the same constructor-injection factory
    server.py itself uses (create_bulk_upload_blueprint), not a second,
    parallel route implementation."""
    storage_backend = mocker.Mock()
    quota_service = mocker.Mock()
    quota_service.check_storage_quota.return_value = None  # default: quota OK

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)
    app.register_blueprint(
        create_bulk_upload_blueprint(
            SessionLocal=db_models["SessionLocal"],
            UserFile=db_models["UserFile"],
            UploadBatch=db_models["UploadBatch"],
            UploadJob=db_models["UploadJob"],
            OutboxEvent=db_models["OutboxEvent"],
            quota_service=quota_service,
            storage_backend=storage_backend,
        )
    )

    with app.app_context():
        access, _ = create_jwt(1)

    test_client = app.test_client()
    test_client.storage_backend = storage_backend
    test_client.quota_service = quota_service
    test_client.access_token = access
    return test_client


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _files(n, ext="pdf", content=b"%PDF fake"):
    return [(io.BytesIO(content), f"file{i}.{ext}") for i in range(n)]


def _upload(client, files, token=None):
    return client.post(
        "/api/uploads/bulk",
        data={"files[]": files},
        headers=_auth(token or client.access_token),
        content_type="multipart/form-data",
    )


# ------------------------------------------------------------ 1. success
def test_bulk_upload_success(client, db_models):
    files = [
        (io.BytesIO(b"%PDF fake"), "a.pdf"),
        (io.BytesIO(b"epub fake"), "b.epub"),
        (io.BytesIO(b"plain text"), "c.txt"),
    ]
    resp = _upload(client, files)
    body = resp.get_json()

    assert resp.status_code == 201, body
    assert body["total_files"] == 3
    assert isinstance(body["batch_id"], int)
    assert len(body["jobs"]) == 3
    assert {j["filename"] for j in body["jobs"]} == {"a.pdf", "b.epub", "c.txt"}
    assert client.storage_backend.upload.call_count == 3

    db = db_models["SessionLocal"]()
    batch = db.get(db_models["UploadBatch"], body["batch_id"])
    jobs = (
        db.execute(
            select(db_models["UploadJob"]).where(
                db_models["UploadJob"].upload_batch_id == batch.id
            )
        )
        .scalars()
        .all()
    )
    db.close()
    assert batch.file_count == 3
    assert len(jobs) == 3
    assert all(j.job_type == "import" and j.status == "pending" for j in jobs)

    status_resp = client.get(
        f"/api/uploads/batch/{batch.id}/status", headers=_auth(client.access_token)
    )
    assert status_resp.status_code == 200, status_resp.get_json()
    assert status_resp.get_json()["total_files"] == 3


# ------------------------------------------------------------ 2. quota
def test_bulk_upload_quota_exceeded(client):
    client.quota_service.check_storage_quota.side_effect = QuotaExceededError(
        "storage quota exceeded", kind="storage", used=999_000_000, limit=1_000_000_000
    )

    resp = _upload(client, _files(1))
    body = resp.get_json()

    assert resp.status_code == 403, body
    assert body["error"] == "storage_quota_exceeded"
    client.storage_backend.upload.assert_not_called()


# ------------------------------------------------------------ 3. invalid type
def test_bulk_upload_invalid_file_type(client):
    files = [
        (io.BytesIO(b"%PDF fake"), "a.pdf"),
        (io.BytesIO(b"\x89PNG fake"), "b.png"),
    ]
    resp = _upload(client, files)
    body = resp.get_json()

    assert resp.status_code == 400, body
    assert body["error"] == "unsupported_type"
    assert "b.png" in body["message"]
    client.storage_backend.upload.assert_not_called()


# ------------------------------------------------------------ 4. too large
def test_bulk_upload_file_too_large(client, mocker):
    import backend.upload.bulk as bulk_module

    mocker.patch.object(
        bulk_module,
        "validate_size",
        side_effect=ValidationError("too_large", "File exceeds the 50 MB limit"),
    )

    resp = _upload(client, _files(1))
    body = resp.get_json()

    assert resp.status_code == 400, body
    assert body["error"] == "too_large"
    client.storage_backend.upload.assert_not_called()


# ------------------------------------------------------------ 5. batch status
def test_bulk_upload_batch_status(client, db_models):
    resp = _upload(client, _files(2))
    batch_id = resp.get_json()["batch_id"]

    db = db_models["SessionLocal"]()
    jobs = (
        db.execute(
            select(db_models["UploadJob"]).where(
                db_models["UploadJob"].upload_batch_id == batch_id
            )
        )
        .scalars()
        .all()
    )
    jobs[0].status = "done"
    jobs[1].status = "failed"
    jobs[1].last_error = "extraction failed"
    db.commit()
    db.close()

    resp = client.get(
        f"/api/uploads/batch/{batch_id}/status", headers=_auth(client.access_token)
    )
    body = resp.get_json()

    assert resp.status_code == 200, body
    assert set(body.keys()) >= {
        "batch_id", "total_files", "processed_files", "failed_files", "status",
        "jobs", "created_at",
    }
    assert body["total_files"] == 2
    assert body["processed_files"] == 2
    assert body["failed_files"] == 1
    assert body["status"] == "done"
    assert len(body["jobs"]) == 2
    for job in body["jobs"]:
        assert set(job.keys()) == {"job_id", "file_id", "filename", "status", "error"}
    failed = next(j for j in body["jobs"] if j["status"] == "failed")
    assert failed["error"] == "extraction failed"


# ------------------------------------------------------------ 6. max files
def test_bulk_upload_max_files_exceeded(client):
    # MAX_BATCH_SIZE defaults to 50 (env-configurable) — this test uses
    # whatever value is actually active rather than hard-coding 50, so it
    # stays correct if MAX_BATCH_SIZE is overridden in the environment.
    resp = _upload(client, _files(MAX_BATCH_SIZE + 1))
    body = resp.get_json()

    assert resp.status_code == 400, body
    assert body["error"] == "too_many_files"
    client.storage_backend.upload.assert_not_called()
