"""API tests for Evidence Retrieval (search / retrieve)."""

from __future__ import annotations

from datetime import datetime, timezone
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
                email=f"ret{user_id}@example.com",
                name=f"Ret {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"RP{user_id}", emoji="R")
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
        hit = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=2,
            quote="Drug X reduces HbA1c",
            claim="Drug X reduces HbA1c",
            study_type="RCT",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"hit-{user_id}",
            provenance_json="{}",
        )
        miss = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=3,
            quote="unrelated biomarker change",
            claim="Biomarker Z shifted",
            study_type="cohort",
            confidence_band="moderate",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"miss-{user_id}",
            provenance_json="{}",
        )
        cand = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=4,
            quote="Drug X reduces HbA1c candidate",
            claim="Drug X reduces HbA1c (candidate)",
            study_type="RCT",
            confidence_band="high",
            status="candidate",
            pipeline_version="2.2.0",
            content_hash=f"cand-{user_id}",
            provenance_json="{}",
        )
        db.add_all([hit, miss, cand])
        db.flush()
        db.add(
            server.WritingSentenceBinding(
                user_id=user_id,
                project_id=project.id,
                document_id=doc.id,
                evidence_object_id=hit.id,
                block_id="blk_ret",
                selected_text="Drug X reduces HbA1c in adults.",
                relation="supports",
            )
        )
        db.commit()
        return {
            "project_id": project.id,
            "document_id": doc.id,
            "hit_id": hit.id,
            "miss_id": miss.id,
            "cand_id": cand.id,
        }
    finally:
        db.close()


def test_search_requires_auth():
    assert _client().post("/api/evidence/search", json={}).status_code in {302, 401}


def test_search_returns_matching_accepted_objects():
    seeded = _seed(7001)
    client = _client()
    _login(client, 7001)
    resp = client.post(
        "/api/evidence/search",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"], "document_id": seeded["document_id"]},
            "filters": {"status": ["accepted"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 10,
            "query_text": "Drug X reduces HbA1c",
            "anchors": {"block_id": "blk_ret", "selected_text": "Drug X reduces HbA1c in adults."},
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["stage"] == "retrieval"
    ids = [o["id"] for o in body["objects"]]
    assert seeded["hit_id"] in ids
    assert seeded["cand_id"] not in ids  # candidate filtered out
    assert body["objects"][0]["id"] == seeded["hit_id"]  # binding + match preference
    assert body["query"]["scope"]["user_id"] == 7001


def test_retrieve_alias_and_rejects_model_knobs():
    seeded = _seed(7002)
    client = _client()
    _login(client, 7002)
    bad = client.post(
        "/api/evidence/retrieve",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "model": "gpt-4",
        },
    )
    assert bad.status_code == 422
    ok = client.post(
        "/api/evidence/retrieve",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "filters": {"status": ["accepted", "candidate"]},
            "result_limit": 50,
        },
    )
    assert ok.status_code == 200
    ids = {o["id"] for o in ok.get_json()["objects"]}
    assert seeded["hit_id"] in ids
    assert seeded["cand_id"] in ids


def test_search_cross_user_project_hidden():
    owner = _seed(7003)
    _seed(7004)
    client = _client()
    _login(client, 7004)
    resp = client.post(
        "/api/evidence/search",
        json={
            "intent": "list_project",
            "scope": {"project_id": owner["project_id"]},
        },
    )
    assert resp.status_code == 404
