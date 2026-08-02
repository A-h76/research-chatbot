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


def test_stale_autosave_returns_version_conflict():
    doc_id = _seed_doc(2003)
    client = _client()
    _login(client, 2003)

    ok = client.post(
        f"/api/writing/documents/{doc_id}/autosave",
        json={
            "title": "Draft",
            "content": "first save",
            "current_version": 1,
            "idempotency_key": "autosave-first",
        },
    )
    assert ok.status_code == 200, ok.get_json()

    stale = client.post(
        f"/api/writing/documents/{doc_id}/autosave",
        json={
            "title": "Draft",
            "content": "stale autosave",
            "current_version": 1,
            "idempotency_key": "autosave-stale",
        },
    )
    assert stale.status_code == 409, stale.get_json()
    body = stale.get_json()
    assert body["error"] == "version_conflict"
    assert body["current_version"] == 2


def test_versions_list_and_restore_round_trip():
    doc_id = _seed_doc(2004, content="v1 body")
    client = _client()
    _login(client, 2004)

    saved = client.post(
        f"/api/writing/documents/{doc_id}/autosave",
        json={
            "title": "Draft",
            "content": "v2 body",
            "current_version": 1,
            "idempotency_key": "restore-seed",
        },
    )
    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()["document"]["current_version"] == 2

    listed = client.get(f"/api/writing/documents/{doc_id}/versions")
    assert listed.status_code == 200, listed.get_json()
    items = listed.get_json()["items"]
    assert len(items) >= 1
    # Prefer restoring the oldest snapshot (pre-autosave) when present
    target = min(items, key=lambda v: int(v["version_no"]))
    restore = client.post(
        f"/api/writing/documents/{doc_id}/restore",
        json={"version_id": target["id"]},
    )
    assert restore.status_code == 200, restore.get_json()
    body = restore.get_json()
    assert body["current_version"] >= 3
    assert body.get("restored_from_version_id") == target["id"]
    assert "content" in body

    again = client.get(f"/api/writing/documents/{doc_id}/versions")
    assert again.status_code == 200
    sources = {v["source"] for v in again.get_json()["items"]}
    assert "restore" in sources

