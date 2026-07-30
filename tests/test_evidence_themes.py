"""API tests for RI-001 Theme Discovery."""

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
                email=f"th{user_id}@example.com",
                name=f"Th {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"T{user_id}", emoji="T")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="t.pdf",
            title="Theme Paper",
            path="/tmp/t.pdf",
            size=10,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        claims = [
            ("Cognitive behavioral therapy reduces anxiety", "RCT"),
            ("Cognitive behavioral therapy for anxiety disorders", "RCT"),
            ("Metformin improves glycemic control diabetes", "cohort"),
            ("Metformin glycemic outcomes type 2 diabetes", "cohort"),
        ]
        eids = []
        for i, (claim, st) in enumerate(claims):
            ev = server.EvidenceObject(
                user_id=user_id,
                project_id=project.id,
                file_id=uf.id,
                page=i + 1,
                quote=claim,
                claim=claim,
                study_type=st,
                study_quality="High",
                supports_json="[]",
                contradicts_json="[]",
                limitations_json="[]",
                confidence_band="high",
                status="accepted",
                pipeline_version="2.2.0",
                content_hash=f"th-{user_id}-{i}",
                provenance_json="{}",
            )
            db.add(ev)
            db.flush()
            eids.append(ev.id)
        db.commit()
        return {
            "user_id": user_id,
            "project_id": project.id,
            "file_id": uf.id,
            "evidence_ids": eids,
        }
    finally:
        db.close()


def test_themes_requires_auth():
    assert _client().get("/api/projects/1/evidence/themes").status_code in {302, 401}


def test_themes_json_reconstructable_and_markdown():
    seeded = _seed(92001)
    client = _client()
    _login(client, seeded["user_id"])

    r1 = client.get(f"/api/projects/{seeded['project_id']}/evidence/themes")
    assert r1.status_code == 200
    body = r1.get_json()
    assert body["stage"] == "themes"
    assert body["themes_version"] == "1.0.0"
    assert body["run"]["input_hash"]
    assert body["metrics"]["theme_count"] >= 1
    assert all("evidence_ids" in t for t in body["themes"])
    for t in body["themes"]:
        for eid in t["evidence_ids"]:
            assert eid in seeded["evidence_ids"]

    r2 = client.get(f"/api/projects/{seeded['project_id']}/evidence/themes")
    assert r2.get_json()["run"]["input_hash"] == body["run"]["input_hash"]
    assert [t["evidence_ids"] for t in r2.get_json()["themes"]] == [
        t["evidence_ids"] for t in body["themes"]
    ]

    md = client.get(f"/api/projects/{seeded['project_id']}/evidence/themes?format=markdown")
    assert md.status_code == 200
    assert b"Theme Discovery" in md.data


def test_themes_bad_threshold_422():
    seeded = _seed(92002)
    client = _client()
    _login(client, seeded["user_id"])
    resp = client.get(
        f"/api/projects/{seeded['project_id']}/evidence/themes?similarity_threshold=2"
    )
    assert resp.status_code == 422
