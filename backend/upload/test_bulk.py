"""Integration tests for POST /api/uploads/bulk and GET
/api/uploads/batch/<id>/status — same standalone Flask + in-memory
SQLite + fake storage backend approach as backend/upload/test_upload.py
(avoids needing a live DB/R2; QuotaService is real to exercise the
actual 403 path).

Run: pytest backend/upload/test_bulk.py -v
"""

import io
from datetime import timedelta

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
from backend.upload.bulk import create_bulk_upload_blueprint
from quotas.models import create_usage_log_model
from quotas.service import QuotaService


class FakeStorageBackend:
    def __init__(self, fail=False):
        self.fail = fail
        self.uploaded = []
        self.deleted = []

    def upload(self, file_obj, key, content_type=None):
        if self.fail:
            raise RuntimeError("simulated storage failure")
        self.uploaded.append((key, content_type, file_obj.read()))
        return key

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
        name = Column(String(300))
        mime = Column(String(120))
        kind = Column(String(20))
        path = Column(String(500))
        size = Column(Integer)

    class UploadBatch(Base):
        __tablename__ = "upload_batches"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        source = Column(String(20))
        file_count = Column(Integer, default=0)
        created_at = Column(DateTime)

    class UploadJob(Base):
        __tablename__ = "upload_jobs"
        id = Column(Integer, primary_key=True)
        upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"))
        file_id = Column(Integer, ForeignKey("files.id"))
        user_id = Column(Integer, ForeignKey("users.id"))
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
        status = Column(String(20), default="pending")

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
        create_bulk_upload_blueprint(
            SessionLocal=SessionLocal,
            UserFile=UserFile,
            UploadBatch=UploadBatch,
            UploadJob=UploadJob,
            OutboxEvent=OutboxEvent,
            quota_service=quota_service,
            storage_backend=storage_backend,
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
        "UploadBatch": UploadBatch,
        "UploadJob": UploadJob,
        "OutboxEvent": OutboxEvent,
        "storage_backend": storage_backend,
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _files(specs):
    """specs: list of (filename, content bytes)."""
    return [(io.BytesIO(content), name) for name, content in specs]


def _upload_bulk(client, token, specs):
    return client.post(
        "/api/uploads/bulk",
        data={"files[]": _files(specs)},
        headers=_auth(token),
        content_type="multipart/form-data",
    )


# ------------------------------------------------------------ success
def test_bulk_upload_success_returns_batch_and_jobs(env):
    resp = _upload_bulk(
        env["client"],
        env["access"],
        [("a.pdf", b"%PDF fake"), ("b.txt", b"hello world")],
    )
    body = resp.get_json()
    assert resp.status_code == 201, body
    assert body["total_files"] == 2
    assert isinstance(body["batch_id"], int)
    assert len(body["jobs"]) == 2
    assert {j["filename"] for j in body["jobs"]} == {"a.pdf", "b.txt"}

    db = env["SessionLocal"]()
    batch = db.get(env["UploadBatch"], body["batch_id"])
    jobs = db.execute(select(env["UploadJob"]).where(env["UploadJob"].upload_batch_id == batch.id)).scalars().all()
    events = db.execute(select(env["OutboxEvent"])).scalars().all()
    db.close()
    assert batch.file_count == 2
    assert len(jobs) == 2
    assert all(j.job_type == "import" and j.status == "pending" for j in jobs)
    assert len(events) == 2


# ------------------------------------------------------------ quota
def test_bulk_upload_quota_exceeded_returns_403_and_uploads_nothing(env):
    db = env["SessionLocal"]()
    db.add(env["StorageUsage"](user_id=1, bytes_used=999_999_990, file_count=1))
    db.commit()
    db.close()

    resp = _upload_bulk(env["client"], env["access"], [("a.pdf", b"x" * 100)])
    body = resp.get_json()
    assert resp.status_code == 403, body
    assert body["error"] == "storage_quota_exceeded"
    assert not env["storage_backend"].uploaded


# ------------------------------------------------------------ validation
def test_bulk_upload_rejects_invalid_extension_and_aborts_whole_batch(env):
    resp = _upload_bulk(
        env["client"],
        env["access"],
        [("a.pdf", b"%PDF fake"), ("malware.exe", b"bad")],
    )
    body = resp.get_json()
    assert resp.status_code == 400, body
    assert body["error"] == "unsupported_type"
    assert not env["storage_backend"].uploaded

    db = env["SessionLocal"]()
    count = len(db.execute(select(env["UserFile"])).scalars().all())
    db.close()
    assert count == 0


def test_bulk_upload_rejects_oversized_file(env, monkeypatch):
    import backend.upload.bulk as bulk_module

    monkeypatch.setattr(bulk_module, "validate_size", _raise_too_large)
    resp = _upload_bulk(env["client"], env["access"], [("a.pdf", b"%PDF fake")])
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "too_large"


def _raise_too_large(*_args, **_kwargs):
    from backend.upload.validation import ValidationError

    raise ValidationError("too_large", "File exceeds the limit")


# ------------------------------------------------------------ batch status
def test_batch_status_reports_progress(env):
    resp = _upload_bulk(
        env["client"],
        env["access"],
        [("a.pdf", b"%PDF fake"), ("b.txt", b"hello")],
    )
    batch_id = resp.get_json()["batch_id"]

    db = env["SessionLocal"]()
    jobs = db.execute(select(env["UploadJob"]).where(env["UploadJob"].upload_batch_id == batch_id)).scalars().all()
    jobs[0].status = "done"
    jobs[1].status = "failed"
    jobs[1].last_error = "extraction failed"
    db.commit()
    db.close()

    status_resp = env["client"].get(f"/api/uploads/batch/{batch_id}/status", headers=_auth(env["access"]))
    body = status_resp.get_json()
    assert status_resp.status_code == 200, body
    assert body["total_files"] == 2
    assert body["processed_files"] == 2
    assert body["failed_files"] == 1
    assert body["status"] == "done"
    failed_job = next(j for j in body["jobs"] if j["status"] == "failed")
    assert failed_job["error"] == "extraction failed"


def test_batch_status_not_found_for_other_users_batch(env):
    resp = _upload_bulk(env["client"], env["access"], [("a.pdf", b"%PDF fake")])
    batch_id = resp.get_json()["batch_id"]

    with env["client"].application.app_context():
        other_access, _ = create_jwt(2)

    status_resp = env["client"].get(f"/api/uploads/batch/{batch_id}/status", headers=_auth(other_access))
    assert status_resp.status_code == 404


# ------------------------------------------------------------ batch size cap
def test_bulk_upload_rejects_more_than_max_batch_size(env, monkeypatch):
    import backend.upload.bulk as bulk_module

    monkeypatch.setattr(bulk_module, "MAX_BATCH_SIZE", 2)
    resp = _upload_bulk(
        env["client"],
        env["access"],
        [("a.pdf", b"x"), ("b.pdf", b"x"), ("c.pdf", b"x")],
    )
    body = resp.get_json()
    assert resp.status_code == 400, body
    assert body["error"] == "too_many_files"
    assert not env["storage_backend"].uploaded


def test_bulk_upload_requires_jwt(env):
    resp = env["client"].post(
        "/api/uploads/bulk",
        data={"files[]": _files([("a.pdf", b"x")])},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401
