"""Regression tests for the storage-quota fix in server.py's upload_file()
(POST /api/files) — it used to compare against the standalone
MAX_STORAGE_MB env var (5000 MB default) while POST /api/documents/upload
went through QuotaService (User.storage_limit_bytes, ~1000 MB default) —
two routes silently enforcing different limits. Both now check the same
column/default; these tests pin that down with small, deterministic
byte counts rather than actually uploading gigabytes.

DATABASE_URL isolation lives in the project's root conftest.py — see
test_chat.py's docstring for why.

Run: pytest test_upload_quota.py -v
"""
import io

import pytest

import server
from server import User, StorageUsage
from quotas import QuotaService


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return server.app.test_client()


def _make_user(db, email, storage_limit_bytes=None, bytes_used=0):
    user = User(email=email, storage_limit_bytes=storage_limit_bytes)
    db.add(user)
    db.commit()
    db.add(StorageUsage(user_id=user.id, bytes_used=bytes_used, file_count=0))
    db.commit()
    return user.id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _upload(client, content=b"hello world file content"):
    return client.post(
        "/api/files",
        data={"file": (io.BytesIO(content), "note.txt")},
        content_type="multipart/form-data",
    )


def test_upload_blocked_at_explicit_per_user_limit(db):
    user_id = _make_user(db, "quota-explicit@test.local", storage_limit_bytes=100, bytes_used=90)
    client = server.app.test_client()
    _login(client, user_id)

    resp = _upload(client, content=b"x" * 20)  # 90 + 20 > 100
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "storage_quota_exceeded"


def test_upload_allowed_within_explicit_per_user_limit(db):
    user_id = _make_user(db, "quota-ok@test.local", storage_limit_bytes=100, bytes_used=50)
    client = server.app.test_client()
    _login(client, user_id)

    resp = _upload(client, content=b"x" * 20)  # 50 + 20 <= 100
    assert resp.status_code == 200


def test_upload_falls_back_to_quota_service_default_not_old_max_storage_mb(db):
    """The regression this whole fix was for: before it, a user with no
    explicit storage_limit_bytes was checked against MAX_STORAGE_MB
    (5000 MB default) here but QuotaService.DEFAULT_STORAGE_LIMIT_BYTES
    (~1000 MB) on /api/documents/upload. Parking bytes_used just under
    the QuotaService default and uploading past it must now 403 — if this
    route were still silently using the old 5000 MB ceiling, it wouldn't."""
    default_limit = QuotaService.DEFAULT_STORAGE_LIMIT_BYTES
    user_id = _make_user(
        db, "quota-default@test.local",
        storage_limit_bytes=None, bytes_used=default_limit - 10,
    )
    client = server.app.test_client()
    _login(client, user_id)

    resp = _upload(client, content=b"x" * 20)  # default_limit - 10 + 20 > default_limit
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "storage_quota_exceeded"
