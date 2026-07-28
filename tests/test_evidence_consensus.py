"""API tests for Evidence Consensus stage."""

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
                email=f"con{user_id}@example.com",
                name=f"Con {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"C{user_id}", emoji="C")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Draft",
            content="Drug X reduces HbA1c.",
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
        support_a = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=1,
            quote="Drug X reduces HbA1c",
            claim="Drug X reduces HbA1c",
            study_type="RCT",
            study_quality="High",
            supports_json=json.dumps(["HbA1c reduction"]),
            contradicts_json="[]",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"sup-a-{user_id}",
            provenance_json="{}",
        )
        support_b = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=2,
            quote="HbA1c fell with Drug X",
            claim="Drug X reduces HbA1c",
            study_type="RCT",
            study_quality="High",
            supports_json=json.dumps(["HbA1c reduction"]),
            contradicts_json="[]",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"sup-b-{user_id}",
            provenance_json="{}",
        )
        contra = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=3,
            quote="Drug X did not change HbA1c",
            claim="Drug X null on HbA1c",
            study_type="cohort",
            study_quality="Moderate",
            supports_json="[]",
            contradicts_json=json.dumps(["HbA1c reduction"]),
            confidence_band="moderate",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"con-{user_id}",
            provenance_json="{}",
        )
        neutral = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=4,
            quote="Background on glycaemia",
            claim="Glycaemia background",
            study_type="review",
            supports_json="[]",
            contradicts_json="[]",
            confidence_band="low",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"neu-{user_id}",
            provenance_json="{}",
        )
        db.add_all([support_a, support_b, contra, neutral])
        db.flush()
        db.add(
            server.WritingSentenceBinding(
                user_id=user_id,
                project_id=project.id,
                document_id=doc.id,
                evidence_object_id=support_a.id,
                block_id="blk_c",
                selected_text="Drug X reduces HbA1c.",
                relation="supports",
            )
        )
        db.add(
            server.WritingSentenceBinding(
                user_id=user_id,
                project_id=project.id,
                document_id=doc.id,
                evidence_object_id=contra.id,
                block_id="blk_c",
                selected_text="Drug X reduces HbA1c.",
                relation="contradicts",
            )
        )
        db.commit()
        return {
            "project_id": project.id,
            "document_id": doc.id,
            "support_a": support_a.id,
            "support_b": support_b.id,
            "contra": contra.id,
            "neutral": neutral.id,
        }
    finally:
        db.close()


def test_consensus_requires_auth():
    assert _client().post("/api/evidence/consensus", json={}).status_code in {302, 401}


def test_consensus_aggregates_supporting_contradicting_neutral():
    seeded = _seed(7201)
    client = _client()
    _login(client, 7201)
    resp = client.post(
        "/api/evidence/consensus",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"], "document_id": seeded["document_id"]},
            "filters": {"status": ["accepted"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 20,
            "query_text": "Drug X reduces HbA1c",
            "anchors": {"block_id": "blk_c", "selected_text": "Drug X reduces HbA1c."},
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["stage"] == "consensus"
    assert body["consensus_version"] == "1.0.0"
    c = body["consensus"]
    assert seeded["support_a"] in c["supporting_ids"]
    assert seeded["contra"] in c["contradicting_ids"]
    assert c["supporting"] >= 1
    assert c["contradicting"] >= 1
    assert c["label"] in {"strong", "moderate", "contested"}
    # Same object set as ranked pipeline — no invented ids
    object_ids = {o["id"] for o in body["objects"]}
    assert set(c["supporting_ids"] + c["contradicting_ids"] + c["neutral_ids"]).issubset(object_ids)


def test_consensus_rejects_model_knobs():
    seeded = _seed(7202)
    client = _client()
    _login(client, 7202)
    bad = client.post(
        "/api/evidence/consensus",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "model": "gpt-4",
        },
    )
    assert bad.status_code == 422


def test_consensus_cross_user_hidden():
    owner = _seed(7203)
    _seed(7204)
    client = _client()
    _login(client, 7204)
    resp = client.post(
        "/api/evidence/consensus",
        json={
            "intent": "list_project",
            "scope": {"project_id": owner["project_id"]},
        },
    )
    assert resp.status_code == 404
