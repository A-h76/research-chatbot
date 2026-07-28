from datetime import datetime, timezone
import os
import time

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed_doc(user_id: int):
    db = server.SessionLocal()
    try:
        user = server.User(
            id=user_id,
            email=f"perf{user_id}@example.com",
            name=f"Perf {user_id}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        project = server.Project(user_id=user_id, name=f"Project {user_id}", emoji="P")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Perf Draft",
            content="hello world",
            status="active",
            current_version=1,
            last_saved_hash="seed-hash",
        )
        db.add(doc)
        db.commit()
        return {"project_id": project.id, "document_id": doc.id}
    finally:
        db.close()


def _duration_ms(fn):
    started = time.perf_counter()
    response = fn()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return response, elapsed_ms


def test_writing_list_and_open_smoke_budget():
    seeded = _seed_doc(3001)
    client = _client()
    _login(client, 3001)

    list_resp, list_ms = _duration_ms(
        lambda: client.get(f"/api/writing/documents?project_id={seeded['project_id']}&status=active")
    )
    assert list_resp.status_code == 200, list_resp.get_json()
    assert list_ms < 500

    open_resp, open_ms = _duration_ms(
        lambda: client.get(f"/api/writing/documents/{seeded['document_id']}")
    )
    assert open_resp.status_code == 200, open_resp.get_json()
    assert open_ms < 500


def test_writing_autosave_smoke_budget():
    seeded = _seed_doc(3002)
    client = _client()
    _login(client, 3002)

    resp, elapsed_ms = _duration_ms(
        lambda: client.post(
            f"/api/writing/documents/{seeded['document_id']}/autosave",
            json={
                "title": "Perf Draft",
                "content": "hello world changed",
                "current_version": 1,
                "idempotency_key": "perf-key-1",
            },
        )
    )
    assert resp.status_code == 200, resp.get_json()
    assert elapsed_ms < 500

