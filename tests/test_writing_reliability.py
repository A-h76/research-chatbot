from datetime import datetime, timezone
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed_doc(user_id: int, *, title: str = "Draft", content: str = "hello world"):
    db = server.SessionLocal()
    try:
        user = server.User(
            id=user_id,
            email=f"reliability{user_id}@example.com",
            name=f"Reliability {user_id}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        project = server.Project(user_id=user_id, name=f"Project {user_id}", emoji="P")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title=title,
            content=content,
            status="active",
            current_version=1,
            last_saved_hash="seed-hash",
        )
        db.add(doc)
        db.commit()
        return doc.id
    finally:
        db.close()


def test_autosave_replay_returns_idempotent_replay_true():
    doc_id = _seed_doc(2001)
    client = _client()
    _login(client, 2001)
    payload = {
        "title": "Draft",
        "content": "hello world changed",
        "current_version": 1,
        "idempotency_key": "same-key-1",
    }
    first = client.post(f"/api/writing/documents/{doc_id}/autosave", json=payload)
    assert first.status_code == 200, first.get_json()
    second = client.post(f"/api/writing/documents/{doc_id}/autosave", json=payload)
    assert second.status_code == 200, second.get_json()
    body = second.get_json()
    assert body["idempotent_replay"] is True
    assert body["unchanged"] is True


def test_stale_version_update_returns_version_conflict_payload():
    doc_id = _seed_doc(2002)
    client = _client()
    _login(client, 2002)

    ok = client.post(
        f"/api/writing/documents/{doc_id}/autosave",
        json={
            "title": "Draft",
            "content": "first save",
            "current_version": 1,
            "idempotency_key": "first-save",
        },
    )
    assert ok.status_code == 200, ok.get_json()

    stale = client.patch(
        f"/api/writing/documents/{doc_id}",
        json={
            "content": "stale overwrite attempt",
            "current_version": 1,
        },
    )
    assert stale.status_code == 409, stale.get_json()
    body = stale.get_json()
    assert body["error"] == "version_conflict"
    assert body["detail"] == "stale_document_version"
    assert body["current_version"] == 2

