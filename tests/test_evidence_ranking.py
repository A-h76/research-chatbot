"""API tests for Evidence Ranking (rank after retrieve)."""

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
                email=f"rank{user_id}@example.com",
                name=f"Rank {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"Rk{user_id}", emoji="R")
        db.add(project)
        db.flush()
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
        weak = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=1,
            quote="Drug X may help",
            claim="Drug X may help",
            study_type="case report",
            study_quality="Low",
            confidence_band="low",
            status="accepted",
            contradicts_json='["rival"]',
            pipeline_version="2.2.0",
            content_hash=f"weak-{user_id}",
            provenance_json="{}",
        )
        strong = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=2,
            quote="Drug X reduces HbA1c in RCT",
            claim="Drug X reduces HbA1c",
            study_type="RCT",
            study_quality="High",
            confidence_band="high",
            status="accepted",
            contradicts_json="[]",
            pipeline_version="2.2.0",
            content_hash=f"strong-{user_id}",
            provenance_json="{}",
        )
        cand = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=3,
            quote="Drug X reduces HbA1c candidate",
            claim="Drug X reduces HbA1c",
            study_type="RCT",
            study_quality="High",
            confidence_band="high",
            status="candidate",
            pipeline_version="2.2.0",
            content_hash=f"cand-rank-{user_id}",
            provenance_json="{}",
        )
        db.add_all([weak, strong, cand])
        db.commit()
        return {
            "project_id": project.id,
            "weak_id": weak.id,
            "strong_id": strong.id,
            "cand_id": cand.id,
        }
    finally:
        db.close()


def test_rank_requires_auth():
    assert _client().post("/api/evidence/rank", json={}).status_code in {302, 401}


def test_rank_orders_strongest_first():
    seeded = _seed(7101)
    client = _client()
    _login(client, 7101)
    resp = client.post(
        "/api/evidence/rank",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "filters": {"status": ["accepted", "candidate"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 20,
            "query_text": "Drug X reduces HbA1c",
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["stage"] == "ranking"
    assert body["ranking_strategy"] == "default_v0"
    assert body["ranking_version"] == "1.1.0"
    assert "ranking_diagnostics" in body
    ids = [o["id"] for o in body["objects"]]
    assert seeded["strong_id"] in ids
    assert seeded["weak_id"] in ids
    # Accepted high RCT before accepted low case-report; candidate after accepted
    assert ids.index(seeded["strong_id"]) < ids.index(seeded["weak_id"])
    if seeded["cand_id"] in ids:
        assert ids.index(seeded["strong_id"]) < ids.index(seeded["cand_id"])


def test_rank_rejects_model_knobs_and_unknown_strategy():
    seeded = _seed(7102)
    client = _client()
    _login(client, 7102)
    bad = client.post(
        "/api/evidence/rank",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "embeddings": True,
        },
    )
    assert bad.status_code == 422
    unknown = client.post(
        "/api/evidence/rank",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "ranking_strategy": "neural_v9",
            "filters": {"status": ["accepted"]},
        },
    )
    assert unknown.status_code == 422


def test_rank_quality_first_strategy_api():
    seeded = _seed(7104)
    client = _client()
    _login(client, 7104)
    resp = client.post(
        "/api/evidence/rank",
        json={
            "intent": "list_project",
            "scope": {"project_id": seeded["project_id"]},
            "filters": {"status": ["accepted", "candidate"], "require_page_anchor": True},
            "ranking_strategy": "quality_first_v1",
            "result_limit": 20,
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["ranking_strategy"] == "quality_first_v1"
    assert body["ranking_diagnostics"]["strategy"] == "quality_first_v1"
    assert seeded["strong_id"] in {o["id"] for o in body["objects"]}


def test_rank_preserves_object_ids_from_retrieval():
    seeded = _seed(7103)
    client = _client()
    _login(client, 7103)
    query = {
        "intent": "list_project",
        "scope": {"project_id": seeded["project_id"]},
        "filters": {"status": ["accepted"], "require_page_anchor": True},
        "ranking_strategy": "default_v0",
        "result_limit": 20,
    }
    search = client.post("/api/evidence/search", json=query)
    rank = client.post("/api/evidence/rank", json=query)
    assert search.status_code == 200 and rank.status_code == 200
    search_ids = {o["id"] for o in search.get_json()["objects"]}
    rank_ids = {o["id"] for o in rank.get_json()["objects"]}
    assert search_ids == rank_ids
