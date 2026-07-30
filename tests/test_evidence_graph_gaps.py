"""API tests for RI-005 graph + RI-006 gaps."""

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
                email=f"gg{user_id}@example.com",
                name=f"GG {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"G{user_id}", emoji="G")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="g.pdf",
            title="Gap Graph Paper",
            path="/tmp/g.pdf",
            size=10,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        for i, (claim, supports, contradicts) in enumerate(
            [
                ("Cognitive therapy reduces anxiety", ["anxiety"], []),
                ("Cognitive therapy for anxiety disorders", ["anxiety"], []),
                ("Drug X null on anxiety", [], ["anxiety"]),
            ]
        ):
            db.add(
                server.EvidenceObject(
                    user_id=user_id,
                    project_id=project.id,
                    file_id=uf.id,
                    page=i + 1,
                    quote=claim,
                    claim=claim,
                    study_type="RCT" if i < 2 else "cohort",
                    study_quality="High",
                    supports_json=json.dumps(supports),
                    contradicts_json=json.dumps(contradicts),
                    limitations_json="[]",
                    confidence_band="high",
                    status="accepted",
                    pipeline_version="2.2.0",
                    content_hash=f"gg-{user_id}-{i}",
                    provenance_json="{}",
                )
            )
        db.commit()
        return {"user_id": user_id, "project_id": project.id, "file_id": uf.id}
    finally:
        db.close()


def test_graph_and_gaps_require_auth():
    c = _client()
    assert c.get("/api/projects/1/evidence/graph").status_code in {302, 401}
    assert c.get("/api/projects/1/evidence/gaps").status_code in {302, 401}


def test_graph_and_gaps_json():
    seeded = _seed(93001)
    client = _client()
    _login(client, seeded["user_id"])

    g = client.get(f"/api/projects/{seeded['project_id']}/evidence/graph")
    assert g.status_code == 200
    body = g.get_json()
    assert body["stage"] == "graph"
    assert body["graph_version"] == "1.0.0"
    assert body["metrics"]["evidence_count"] == 3
    assert any(n["type"] == "paper" for n in body["nodes"])
    assert any(e["type"] == "from" for e in body["edges"])

    gaps = client.get(f"/api/projects/{seeded['project_id']}/evidence/gaps")
    assert gaps.status_code == 200
    gbody = gaps.get_json()
    assert gbody["stage"] == "gaps"
    assert gbody["gaps_version"] == "1.0.0"
    assert gbody["metrics"]["gap_count"] >= 1
    md = client.get(f"/api/projects/{seeded['project_id']}/evidence/gaps?format=markdown")
    assert md.status_code == 200
    assert b"Research Gaps" in md.data
