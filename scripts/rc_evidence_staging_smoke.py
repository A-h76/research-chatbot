"""Staging smoke for Evidence Layer RC — uses live DATABASE_URL (Postgres).

Run: python scripts/rc_evidence_staging_smoke.py
Does not go through pytest/conftest (avoids SQLite override).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))
url = (os.environ.get("DATABASE_URL") or "").replace("postgres://", "postgresql://", 1)
if not url.startswith("postgresql"):
    print("FAIL: DATABASE_URL is not Postgres")
    sys.exit(2)

# Bind engine before importing server — server reads DATABASE_URL at import.
os.environ["DATABASE_URL"] = url
os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server  # noqa: E402
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import save_analysis_result


def main() -> int:
    client = server.app.test_client()
    uid_a, uid_b = 91001, 91002
    now = datetime.now(timezone.utc)

    db = server.SessionLocal()
    try:
        for uid in (uid_a, uid_b):
            if db.get(server.User, uid) is None:
                db.add(
                    server.User(
                        id=uid,
                        email=f"rc{uid}@example.com",
                        name=f"RC {uid}",
                        created_at=now,
                    )
                )
        db.flush()
        proj = server.Project(user_id=uid_a, name="RC Evidence Smoke", emoji="R")
        db.add(proj)
        db.flush()
        doc = server.WritingDocument(
            user_id=uid_a,
            project_id=proj.id,
            title="RC draft",
            content="Drug X reduces HbA1c in adults.",
            status="active",
            current_version=1,
            last_saved_hash="rc",
        )
        db.add(doc)
        uf = server.UserFile(
            user_id=uid_a,
            project_id=proj.id,
            name="rc-paper.pdf",
            title="RC Paper",
            path="/tmp/rc-paper.pdf",
            size=100,
            meta_status="done",
            kind="document",
            content_hash="rc-hash-staging",
        )
        db.add(uf)
        db.flush()
        db.add(
            server.Chunk(
                file_id=uf.id,
                idx=0,
                content="Drug X reduces HbA1c.",
                page=2,
                section="results",
            )
        )
        save_analysis_result(
            db,
            server.AnalysisPipelineResult,
            AnalysisResult(
                file_id=uf.id,
                content_hash="rc-hash-staging",
                status=AnalysisJobStatus.DONE,
                phase_results={
                    "classification": {"study_design": {"label": "randomized_controlled_trial"}},
                    "evidence_grading": {
                        "study_quality": "high",
                        "risk_of_bias": {"overall_risk": "low"},
                    },
                    "knowledge_graph": {
                        "version": "1.0.0",
                        "nodes": [
                            {
                                "node_id": "c1",
                                "node_type": "evidence_claim",
                                "label": "Drug X reduces HbA1c",
                                "evidence_references": [
                                    {
                                        "page": 2,
                                        "section": "results",
                                        "text_snippet": "Drug X reduces HbA1c",
                                    }
                                ],
                            }
                        ],
                        "edges": [],
                    },
                },
                pipeline_version="2.0.0",
                total_processing_time_ms=1,
            ),
            user_id=uid_a,
        )
        db.commit()
        project_id, document_id, file_id = proj.id, doc.id, uf.id
    finally:
        db.close()

    with client.session_transaction() as sess:
        sess["user_id"] = uid_a

    extract = client.post(
        f"/api/projects/{project_id}/evidence/extract",
        json={"file_id": file_id},
    )
    print("extract_status", extract.status_code, extract.get_json())
    assert extract.status_code == 200, extract.get_json()
    assert extract.get_json().get("status") in {"succeeded", "skipped"}

    listed = client.get(f"/api/projects/{project_id}/evidence")
    assert listed.status_code == 200
    items = listed.get_json()["items"]
    assert items, "expected extracted candidates"
    eid = items[0]["id"]

    bind = client.post(
        f"/api/documents/{document_id}/evidence-bindings",
        json={
            "evidence_object_id": eid,
            "block_id": "rc_blk",
            "selected_text": "Drug X reduces HbA1c in adults.",
            "relation": "supports",
        },
    )
    print("bind_status", bind.status_code)
    assert bind.status_code == 201, bind.get_json()

    # Accept so explain can be sufficient
    rev = client.post(f"/api/evidence/{eid}/reviews", json={"status": "accepted"})
    assert rev.status_code == 200, rev.get_json()

    explain = client.post(
        "/api/evidence/explain",
        json={
            "document_id": document_id,
            "project_id": project_id,
            "block_id": "rc_blk",
            "selected_text": "Drug X reduces HbA1c in adults.",
        },
    )
    body = explain.get_json()
    print("explain_status", explain.status_code, body.get("sufficiency"), "n=", len(body.get("evidence") or []))
    assert explain.status_code == 200
    assert body["sufficiency"] == "sufficient"
    assert body["evidence"][0]["id"] == eid

    # Cross-user IDOR
    with client.session_transaction() as sess:
        sess["user_id"] = uid_b
    idor = client.get(f"/api/evidence/{eid}")
    print("idor_status", idor.status_code)
    assert idor.status_code == 404

    print("STAGING_SMOKE_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("STAGING_SMOKE_FAIL", type(exc).__name__, exc)
        raise
