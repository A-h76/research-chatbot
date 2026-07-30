"""API contract: durable reviewer runs reconstruct historical reviews (A-401 / A-503)."""

from __future__ import annotations

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
        db.add(
            server.User(
                id=user_id,
                email=f"rr{user_id}@example.com",
                name=f"Rr {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"R{user_id}", emoji="R")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Draft",
            content="Drug X reduces HbA1c in adults.",
            status="active",
            current_version=2,
            last_saved_hash="h",
        )
        db.add(doc)
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="p.pdf",
            title="Paper",
            path="/tmp/p.pdf",
            size=10,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        support = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=2,
            quote="Drug X reduces HbA1c in adults",
            claim="Drug X reduces HbA1c in adults",
            study_type="RCT",
            study_quality="High",
            supports_json=json.dumps(["HbA1c reduction"]),
            contradicts_json="[]",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"rr-sup-{user_id}",
            provenance_json="{}",
        )
        db.add(support)
        db.flush()
        db.add(
            server.WritingSentenceBinding(
                user_id=user_id,
                project_id=project.id,
                document_id=doc.id,
                evidence_object_id=support.id,
                block_id="blk_rr",
                selected_text="Drug X reduces HbA1c in adults.",
                relation="supports",
            )
        )
        db.commit()
        return {"project_id": project.id, "document_id": doc.id, "support_id": support.id}
    finally:
        db.close()


def test_writing_persists_reviewer_run_and_reconstructs():
    seeded = _seed(7601)
    client = _client()
    _login(client, 7601)

    resp = client.post(
        "/api/evidence/writing",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"], "document_id": seeded["document_id"]},
            "filters": {"status": ["accepted"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 20,
            "query_text": "Drug X reduces HbA1c",
            "anchors": {"block_id": "blk_rr", "selected_text": "Drug X reduces HbA1c in adults."},
        },
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    writing = body.get("writing") or {}
    assert writing.get("review") is not None
    run_id = writing.get("reviewer_run_id")
    assert isinstance(run_id, int) and run_id > 0

    latest = client.get(f"/api/documents/{seeded['document_id']}/reviewer-runs/latest")
    assert latest.status_code == 200
    latest_body = latest.get_json()
    assert latest_body["id"] == run_id
    assert latest_body["document_version_no"] == 2
    assert latest_body["reviewer_version"]
    assert "findings" in latest_body
    assert "review" in latest_body
    assert latest_body["review"]["issue_count"] == latest_body["issue_count"]
    assert "input_snapshot" in latest_body

    by_id = client.get(f"/api/reviewer-runs/{run_id}")
    assert by_id.status_code == 200
    assert by_id.get_json()["id"] == run_id

    listed = client.get(f"/api/documents/{seeded['document_id']}/reviewer-runs")
    assert listed.status_code == 200
    items = listed.get_json()["items"]
    assert any(i["id"] == run_id for i in items)

    db = server.SessionLocal()
    try:
        events = (
            db.execute(
                server.select(server.OutboxEvent).where(
                    server.OutboxEvent.event_type == "ReviewCompleted",
                    server.OutboxEvent.aggregate_id == seeded["document_id"],
                )
            )
            .scalars()
            .all()
        )
        assert events
        payload = json.loads(events[-1].payload)
        assert payload["reviewer_run_id"] == run_id
        assert "issue_count" in payload
    finally:
        db.close()


def test_reviewer_run_requires_ownership():
    seeded = _seed(7602)
    _seed(7603)
    client = _client()
    _login(client, 7603)
    resp = client.get(f"/api/documents/{seeded['document_id']}/reviewer-runs/latest")
    assert resp.status_code in {403, 404}
