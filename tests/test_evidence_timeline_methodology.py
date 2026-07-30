"""API tests for RI-007 timeline + RI-008 methodology."""

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
                email=f"tm{user_id}@example.com",
                name=f"TM {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"TM{user_id}", emoji="T")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="tm.pdf",
            title="Timeline Paper",
            year="2019",
            path="/tmp/tm.pdf",
            size=10,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        for i, (claim, st, supports) in enumerate(
            [
                ("Cognitive therapy reduces anxiety", "RCT", ["anxiety"]),
                ("Cognitive therapy anxiety outcomes", "RCT", ["anxiety"]),
                ("Observational anxiety cohort", "cohort", ["anxiety"]),
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
                    study_type=st,
                    study_quality="High",
                    supports_json=json.dumps(supports),
                    contradicts_json="[]",
                    limitations_json=json.dumps(["Short follow-up"]),
                    confidence_band="high",
                    status="accepted",
                    pipeline_version="2.2.0",
                    content_hash=f"tm-{user_id}-{i}",
                    provenance_json=json.dumps({"statistics": "t-test"}),
                )
            )
        db.commit()
        return {"user_id": user_id, "project_id": project.id, "file_id": uf.id}
    finally:
        db.close()


def test_timeline_methodology_auth():
    c = _client()
    assert c.get("/api/projects/1/evidence/timeline").status_code in {302, 401}
    assert c.get("/api/projects/1/evidence/methodology").status_code in {302, 401}


def test_timeline_and_methodology_json():
    seeded = _seed(94001)
    client = _client()
    _login(client, seeded["user_id"])

    tl = client.get(f"/api/projects/{seeded['project_id']}/evidence/timeline")
    assert tl.status_code == 200
    body = tl.get_json()
    assert body["stage"] == "timeline"
    assert body["timeline_version"] == "1.0.0"
    assert body["span"]["start_year"] == 2019
    assert any(e["year"] == 2019 for e in body["entries"])

    meth = client.get(f"/api/projects/{seeded['project_id']}/evidence/methodology")
    assert meth.status_code == 200
    mbody = meth.get_json()
    assert mbody["stage"] == "methodology"
    assert mbody["methodology_version"] == "1.0.0"
    assert mbody["metrics"]["card_count"] >= 1
    assert all(c["tone"] == "advisory" for c in mbody["cards"])
