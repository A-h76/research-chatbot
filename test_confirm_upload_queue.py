"""confirm_upload() must enqueue an import job — never process inline.

Pins the dual-path fix: upload_file() and confirm_upload() share the
transactional-outbox pattern (import → phase1_analysis → paper_analysis).

Run: pytest test_confirm_upload_queue.py -v
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import server


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user(db):
    u = server.User(email=f"confirm-{server.uuid.uuid4().hex[:8]}@example.com", name="T", auth_provider="dev")
    db.add(u)
    db.commit()
    return u


def test_confirm_upload_enqueues_import_not_process_document(db, user, monkeypatch):
    key = f"users/{user.id}/{server.uuid.uuid4().hex}.txt"
    us = server.UploadSession(
        user_id=user.id,
        key=key,
        name="paper.txt",
        mime="text/plain",
        size_expected=12,
        checksum_sha256=None,
        status="pending",
    )
    db.add(us)
    db.commit()

    provider = MagicMock()
    provider.head.return_value = SimpleNamespace(size=12, etag=None)
    provider.local_copy.return_value.__enter__ = lambda self: "/tmp/fake.txt"
    provider.local_copy.return_value.__exit__ = lambda *a: False

    monkeypatch.setattr(server.storage.storage_manager, "provider", provider)
    monkeypatch.setattr(
        server,
        "validate_upload_path",
        lambda *a, **k: ("txt", "text/plain"),
    )
    process_spy = MagicMock()
    monkeypatch.setattr(server, "_process_document", process_spy)

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    resp = client.post("/api/uploads/confirm", json={"session_id": us.id})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body.get("job_id") is not None
    assert body.get("note") is None
    process_spy.assert_not_called()

    job = db.get(server.UploadJob, body["job_id"])
    assert job is not None
    assert job.job_type == "import"
    assert job.status == "pending"
    assert job.file_id == body["id"]

    events = (
        db.execute(
            server.select(server.OutboxEvent).where(server.OutboxEvent.aggregate_id == job.id)
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].event_type == "job.enqueued"
