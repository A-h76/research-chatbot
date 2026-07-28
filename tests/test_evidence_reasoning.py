"""API tests for Evidence Reasoning stage."""

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
                email=f"rsn{user_id}@example.com",
                name=f"Rsn {user_id}",
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
        support = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=1,
            quote="In adults, Drug X 10 mg once daily reduced HbA1c",
            claim="Drug X reduces HbA1c in adults at 10 mg",
            study_type="RCT",
            study_quality="High",
            supports_json=json.dumps(["HbA1c reduction"]),
            contradicts_json="[]",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"rsn-sup-{user_id}",
            provenance_json="{}",
        )
        contra = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=2,
            quote="In children, Drug X 5 mg did not change HbA1c",
            claim="Drug X null on HbA1c in children at 5 mg",
            study_type="cohort",
            study_quality="Moderate",
            supports_json="[]",
            contradicts_json=json.dumps(["HbA1c reduction"]),
            confidence_band="moderate",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"rsn-con-{user_id}",
            provenance_json="{}",
        )
        db.add_all([support, contra])
        db.flush()
        db.add(
            server.WritingSentenceBinding(
                user_id=user_id,
                project_id=project.id,
                document_id=doc.id,
                evidence_object_id=support.id,
                block_id="blk_rsn",
                selected_text="Drug X reduces HbA1c in adults.",
                relation="supports",
            )
        )
        db.add(
            server.WritingSentenceBinding(
                user_id=user_id,
                project_id=project.id,
                document_id=doc.id,
                evidence_object_id=contra.id,
                block_id="blk_rsn",
                selected_text="Drug X reduces HbA1c in adults.",
                relation="contradicts",
            )
        )
        db.commit()
        return {
            "project_id": project.id,
            "document_id": doc.id,
            "support_id": support.id,
            "contra_id": contra.id,
        }
    finally:
        db.close()


def test_reason_requires_auth():
    assert _client().post("/api/evidence/reason", json={}).status_code in {302, 401}


def test_reason_returns_structured_chain():
    seeded = _seed(7401)
    client = _client()
    _login(client, 7401)
    resp = client.post(
        "/api/evidence/reason",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"], "document_id": seeded["document_id"]},
            "filters": {"status": ["accepted"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 20,
            "query_text": "Drug X reduces HbA1c",
            "anchors": {"block_id": "blk_rsn", "selected_text": "Drug X reduces HbA1c in adults."},
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["stage"] == "reasoning"
    assert body["reasoning_version"] == "1.0.0"
    r = body["reasoning"]
    assert r["summary_code"] in {
        "strong",
        "moderate",
        "contested",
        "contested_with_mediators",
        "opposed",
        "none",
        "insufficient",
    }
    step_names = [s["step"] for s in r["steps"]]
    assert step_names == ["retrieval", "ranking", "consensus", "conflict", "conclusion"]
    assert seeded["support_id"] in r["evidence_ids"]
    assert seeded["contra_id"] in r["evidence_ids"]
    object_ids = {o["id"] for o in body["objects"]}
    assert set(r["evidence_ids"]).issubset(object_ids)
    # Prior stages echoed
    assert body.get("consensus") is not None
    assert body.get("conflict") is not None


def test_reason_rejects_model_knobs():
    seeded = _seed(7402)
    client = _client()
    _login(client, 7402)
    bad = client.post(
        "/api/evidence/reason",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "prompt": "explain this",
        },
    )
    assert bad.status_code == 422


def test_reason_cross_user_hidden():
    owner = _seed(7403)
    _seed(7404)
    client = _client()
    _login(client, 7404)
    resp = client.post(
        "/api/evidence/reason",
        json={
            "intent": "list_project",
            "scope": {"project_id": owner["project_id"]},
        },
    )
    assert resp.status_code == 404
