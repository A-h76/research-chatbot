"""Evidence Layer API security + explain contract tests."""

from datetime import datetime, timezone
import json
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed(user_id: int):
    db = server.SessionLocal()
    try:
        user = server.User(
            id=user_id,
            email=f"ev{user_id}@example.com",
            name=f"Ev {user_id}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        project = server.Project(user_id=user_id, name=f"P{user_id}", emoji="E")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Draft",
            content="Sentence one. Sentence two.",
            status="active",
            current_version=1,
            last_saved_hash="seed",
        )
        db.add(doc)
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="paper.pdf",
            title="Paper A",
            path="/tmp/paper.pdf",
            size=100,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        # Fake chunks attribute if Column expects int — check UserFile.chunks
        ev = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=2,
            quote="significant reduction",
            claim="Drug X reduces outcome Y",
            study_type="RCT",
            study_quality="high",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"hash-{user_id}",
            provenance_json=json.dumps({"pipeline_version": "2.2.0"}),
        )
        db.add(ev)
        db.flush()
        binding = server.WritingSentenceBinding(
            user_id=user_id,
            project_id=project.id,
            document_id=doc.id,
            evidence_object_id=ev.id,
            block_id="blk_1",
            range_start=0,
            range_end=12,
            selected_text="Sentence one.",
            relation="supports",
        )
        db.add(binding)
        db.commit()
        return {
            "project_id": project.id,
            "document_id": doc.id,
            "file_id": uf.id,
            "evidence_id": ev.id,
        }
    finally:
        db.close()


def test_explain_requires_auth():
    resp = _client().post("/api/evidence/explain", json={})
    assert resp.status_code in {302, 401}


def test_explain_sufficient():
    seeded = _seed(2101)
    client = _client()
    _login(client, 2101)
    resp = client.post(
        "/api/evidence/explain",
        json={
            "document_id": seeded["document_id"],
            "project_id": seeded["project_id"],
            "block_id": "blk_1",
            "selected_text": "Sentence one.",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sufficiency"] == "sufficient"
    assert body["evidence"][0]["id"] == seeded["evidence_id"]
    assert body["evidence"][0]["status"] == "accepted"


def test_explain_insufficient_without_binding():
    seeded = _seed(2102)
    client = _client()
    _login(client, 2102)
    resp = client.post(
        "/api/evidence/explain",
        json={
            "document_id": seeded["document_id"],
            "project_id": seeded["project_id"],
            "block_id": "missing",
            "selected_text": "Nope",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sufficiency"] == "insufficient"
    assert body["evidence"] == []


def test_cross_user_evidence_hidden():
    owner = _seed(2103)
    _seed(2104)
    client = _client()
    _login(client, 2104)
    resp = client.get(f"/api/evidence/{owner['evidence_id']}")
    assert resp.status_code == 404


def test_review_accept():
    seeded = _seed(2105)
    db = server.SessionLocal()
    try:
        ev = db.get(server.EvidenceObject, seeded["evidence_id"])
        ev.status = "candidate"
        db.commit()
    finally:
        db.close()
    client = _client()
    _login(client, 2105)
    resp = client.post(
        f"/api/evidence/{seeded['evidence_id']}/reviews",
        json={"status": "accepted"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["evidence"]["status"] == "accepted"
