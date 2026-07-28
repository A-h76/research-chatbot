from datetime import datetime, timezone
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed_user_project_document(user_id: int, *, title: str = "Draft"):
    db = server.SessionLocal()
    try:
        user = server.User(
            id=user_id,
            email=f"user{user_id}@example.com",
            name=f"User {user_id}",
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
            content="hello world",
            status="active",
            current_version=1,
            last_saved_hash="seed",
        )
        db.add(doc)
        db.commit()
        return {"project_id": project.id, "document_id": doc.id}
    finally:
        db.close()


def test_writing_document_requires_authentication():
    resp = _client().get("/api/writing/documents?project_id=1")
    assert resp.status_code in {302, 401}


def test_cross_user_document_access_is_hidden():
    owner = _seed_user_project_document(1001)
    _seed_user_project_document(1002)
    client = _client()
    _login(client, 1002)
    resp = client.get(f"/api/writing/documents/{owner['document_id']}")
    assert resp.status_code == 404


def test_deleted_document_autosave_is_rejected():
    seeded = _seed_user_project_document(1003, title="Deleted doc")
    db = server.SessionLocal()
    try:
        doc = db.get(server.WritingDocument, seeded["document_id"])
        doc.status = "deleted"
        db.commit()
    finally:
        db.close()

    client = _client()
    _login(client, 1003)
    resp = client.post(
        f"/api/writing/documents/{seeded['document_id']}/autosave",
        json={
            "title": "Deleted doc",
            "content": "new text",
            "current_version": 1,
            "idempotency_key": "deleted-1",
        },
    )
    assert resp.status_code == 400
    assert resp.get_json()["detail"] == "deleted_documents_are_read_only"

