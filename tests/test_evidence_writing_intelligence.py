"""API tests for Writing Intelligence stage."""

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


def _seed(user_id: int, *, with_support: bool = True):
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=user_id,
                email=f"wi{user_id}@example.com",
                name=f"Wi {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"W{user_id}", emoji="W")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Draft",
            content="Drug X reduces HbA1c in adults.",
            status="active",
            current_version=1,
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
        ids = {"project_id": project.id, "document_id": doc.id}
        if with_support:
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
                content_hash=f"wi-sup-{user_id}",
                provenance_json="{}",
            )
            support2 = server.EvidenceObject(
                user_id=user_id,
                project_id=project.id,
                file_id=uf.id,
                page=3,
                quote="HbA1c fell at 12 weeks with Drug X",
                claim="HbA1c reduction persists at 12 weeks",
                study_type="RCT",
                study_quality="High",
                supports_json=json.dumps(["HbA1c reduction"]),
                contradicts_json="[]",
                confidence_band="high",
                status="accepted",
                pipeline_version="2.2.0",
                content_hash=f"wi-sup2-{user_id}",
                provenance_json="{}",
            )
            db.add_all([support, support2])
            db.flush()
            db.add(
                server.WritingSentenceBinding(
                    user_id=user_id,
                    project_id=project.id,
                    document_id=doc.id,
                    evidence_object_id=support.id,
                    block_id="blk_wi",
                    selected_text="Drug X reduces HbA1c in adults.",
                    relation="supports",
                )
            )
            db.add(
                server.WritingSentenceBinding(
                    user_id=user_id,
                    project_id=project.id,
                    document_id=doc.id,
                    evidence_object_id=support2.id,
                    block_id="blk_wi",
                    selected_text="Drug X reduces HbA1c in adults.",
                    relation="supports",
                )
            )
            ids["support_id"] = support.id
            ids["support2_id"] = support2.id
        db.commit()
        return ids
    finally:
        db.close()


def test_writing_requires_auth():
    assert _client().post("/api/evidence/writing", json={}).status_code in {302, 401}


def test_writing_generates_grounded_paragraph():
    seeded = _seed(7501)
    client = _client()
    _login(client, 7501)
    resp = client.post(
        "/api/evidence/writing",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"], "document_id": seeded["document_id"]},
            "filters": {"status": ["accepted"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 20,
            "query_text": "Drug X reduces HbA1c",
            "anchors": {"block_id": "blk_wi", "selected_text": "Drug X reduces HbA1c in adults."},
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["stage"] == "writing"
    assert body["writing_version"] == "1.3.1"
    w = body["writing"]
    assert w["status"] == "ok"
    assert w["mode"] == "grounded_v0"
    assert w["paragraph"]
    assert w.get("sections")
    assert w.get("metrics") is not None
    assert w.get("review") is not None
    assert "Drug X reduces HbA1c" in w["paragraph"]
    cite_ids = {c["evidence_id"] for c in w["citations"]}
    assert cite_ids.issubset({seeded["support_id"], seeded["support2_id"]})
    object_ids = {o["id"] for o in body["objects"]}
    assert cite_ids.issubset(object_ids)
    assert body.get("reasoning") is not None


def test_writing_blocks_without_evidence():
    seeded = _seed(7502, with_support=False)
    client = _client()
    _login(client, 7502)
    resp = client.post(
        "/api/evidence/writing",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"], "document_id": seeded["document_id"]},
            "filters": {"status": ["accepted"]},
            "query_text": "Drug X reduces HbA1c",
        },
    )
    assert resp.status_code == 200, resp.get_json()
    w = resp.get_json()["writing"]
    assert w["status"] == "blocked"
    assert w["paragraph"] is None
    assert w["blocked_reason"] in {
        "insufficient_evidence",
        "no_supporting_evidence",
        "opposed_evidence",
    }


def test_writing_rejects_model_knobs():
    seeded = _seed(7503)
    client = _client()
    _login(client, 7503)
    bad = client.post(
        "/api/evidence/writing",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"]},
            "model": "gpt-4o",
        },
    )
    assert bad.status_code == 422
