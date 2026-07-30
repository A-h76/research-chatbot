"""API tests for RI-002 Evidence Matrix."""

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
                email=f"mx{user_id}@example.com",
                name=f"Mx {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"M{user_id}", emoji="M")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="paper.pdf",
            title="Matrix Paper",
            year="2021",
            path="/tmp/mx.pdf",
            size=10,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        ev = server.EvidenceObject(
            user_id=user_id,
            project_id=project.id,
            file_id=uf.id,
            page=1,
            quote="Effect observed",
            claim="Treatment improves outcome",
            study_type="RCT",
            study_quality="High",
            supports_json=json.dumps(["outcome"]),
            contradicts_json="[]",
            limitations_json=json.dumps(["Short follow-up"]),
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"mx-{user_id}",
            provenance_json=json.dumps({"dataset": "Trial DB"}),
        )
        db.add(ev)
        pa = server.PaperAnalysis(
            file_id=uf.id,
            user_id=user_id,
            status="done",
            data=json.dumps(
                {
                    "methodology": "should not override RCT",
                    "dataset": "ignored when provenance present",
                }
            ),
        )
        db.add(pa)
        db.commit()
        return {"user_id": user_id, "project_id": project.id, "file_id": uf.id, "evidence_id": ev.id}
    finally:
        db.close()


def test_matrix_requires_auth():
    assert _client().get("/api/projects/1/evidence/matrix").status_code in {302, 401}


def test_matrix_json_and_exports():
    seeded = _seed(91002)
    client = _client()
    _login(client, seeded["user_id"])

    resp = client.get(f"/api/projects/{seeded['project_id']}/evidence/matrix")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["stage"] == "matrix"
    assert body["matrix_version"] == "1.0.0"
    assert body["project_id"] == seeded["project_id"]
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["file_id"] == seeded["file_id"]
    assert row["method"]["value"] == "RCT"
    assert seeded["evidence_id"] in row["method"]["evidence_ids"]
    assert row["dataset"]["value"] == "Trial DB"
    assert "Treatment improves" in row["findings"]["value"]
    assert row["limitations"]["status"] == "known"
    assert body["metrics"]["paper_count"] == 1

    md = client.get(f"/api/projects/{seeded['project_id']}/evidence/matrix?format=markdown")
    assert md.status_code == 200
    assert "text/markdown" in md.content_type
    assert b"| Paper | Method |" in md.data
    assert b"RCT" in md.data

    csv_resp = client.get(f"/api/projects/{seeded['project_id']}/evidence/matrix?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.content_type
    assert b"file_id,paper_title" in csv_resp.data


def test_matrix_bad_format_422():
    seeded = _seed(91003)
    client = _client()
    _login(client, seeded["user_id"])
    resp = client.get(f"/api/projects/{seeded['project_id']}/evidence/matrix?format=xlsx")
    assert resp.status_code == 422
