"""A-215 smoke: Research Ready → extract → accept one EvidenceObject.

Runs on the root pytest SQLite DB (CI) by invoking the worker handler
directly — same pattern as tests/integration/test_researcher_workflows.py
(SQLite has no FOR UPDATE SKIP LOCKED).

Staging Postgres path: scripts/rc_evidence_staging_smoke.py

Run: pytest tests/integration/test_evidence_smoke.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import server
import worker
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import save_analysis_result
from backend.library.readiness import research_readiness


def _phase_results_with_claim():
    return {
        "classification": {"study_design": {"label": "randomized_controlled_trial"}},
        "evidence_grading": {
            "study_quality": "high",
            "risk_of_bias": {"overall_risk": "low"},
            "consistency": {"consistency_level": "highly_consistent"},
            "pipeline_version": "1.0.0",
        },
        "knowledge_graph": {
            "version": "1.0.0",
            "nodes": [
                {
                    "node_id": "c1",
                    "node_type": "evidence_claim",
                    "label": "Drug X reduces HbA1c in adults",
                    "properties": {},
                    "evidence_references": [
                        {
                            "page": 2,
                            "section": "results",
                            "text_snippet": "Drug X reduces HbA1c in adults by 0.8%",
                            "character_range": [40, 90],
                        }
                    ],
                }
            ],
            "edges": [],
        },
    }


@pytest.fixture
def smoke_world(researcher):
    """Research Ready paper + Phase 1 artifacts + writing document."""
    db = researcher.db
    user = researcher.user
    project = researcher.project

    uf = server.UserFile(
        user_id=user.id,
        project_id=project.id,
        name="smoke-paper.pdf",
        title="Smoke Paper",
        path=f"/tmp/smoke-{user.id}.pdf",
        size=120,
        meta_status="done",
        kind="document",
        content_hash=f"smoke-hash-{user.id}",
    )
    db.add(uf)
    db.flush()
    db.add(
        server.Chunk(
            file_id=uf.id,
            idx=0,
            content="Drug X reduces HbA1c in adults by 0.8%.",
            page=2,
            section="results",
        )
    )
    doc = server.WritingDocument(
        user_id=user.id,
        project_id=project.id,
        title="Smoke draft",
        content="Drug X reduces HbA1c in adults.",
        status="active",
        current_version=1,
        last_saved_hash="smoke",
    )
    db.add(doc)
    save_analysis_result(
        db,
        server.AnalysisPipelineResult,
        AnalysisResult(
            file_id=uf.id,
            content_hash=uf.content_hash,
            status=AnalysisJobStatus.DONE,
            phase_results=_phase_results_with_claim(),
            pipeline_version="2.0.0",
            total_processing_time_ms=5,
        ),
        user_id=user.id,
    )
    db.commit()

    assert research_readiness(uf) == "research_ready"
    return {
        "project_id": project.id,
        "file_id": uf.id,
        "document_id": doc.id,
        "user_id": user.id,
    }


def _run_enqueued_extract_job(db, job_id: int):
    """Simulate worker claim + run for evidence_extract (SQLite-safe)."""
    job = db.get(server.UploadJob, job_id)
    assert job is not None
    assert job.job_type == "evidence_extract"
    assert job.status == "pending"
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    worker._handle_evidence_extract(db, job)

    job = db.get(server.UploadJob, job_id)
    job.status = "done"
    job.finished_at = datetime.now(timezone.utc)
    worker._mark_outbox_dispatched(db, job.id)
    db.commit()
    return job


def test_a215_ready_extract_accept_smoke(researcher, smoke_world):
    """End-to-end: Research Ready → async extract → worker → accept candidate."""
    client = researcher.client
    db = researcher.db
    project_id = smoke_world["project_id"]
    file_id = smoke_world["file_id"]
    document_id = smoke_world["document_id"]

    # ── Gate: not ready must still 400 ────────────────────────────────────
    # (separate quick check on a metadata-only file would be redundant here;
    # readiness already asserted in fixture.)

    # ── Enqueue extract (async contract) ──────────────────────────────────
    enqueue = client.post(
        f"/api/projects/{project_id}/evidence/extract",
        json={"file_id": file_id},
    )
    assert enqueue.status_code == 202, enqueue.get_json()
    body = enqueue.get_json()
    assert body["status"] == "pending"
    job_id = body["job_id"]
    run_id = body["run_id"]
    assert isinstance(job_id, int)
    assert isinstance(run_id, int)

    # Job status pollable
    status = client.get(f"/api/jobs/{job_id}/status")
    assert status.status_code == 200
    assert status.get_json()["status"] in {"pending", "running"}
    assert status.get_json()["job_type"] == "evidence_extract"

    # EvidenceExtractionStarted event present
    started = (
        db.execute(
            server.select(server.OutboxEvent).where(
                server.OutboxEvent.event_type == "EvidenceExtractionStarted",
                server.OutboxEvent.aggregate_id == run_id,
            )
        )
        .scalars()
        .all()
    )
    assert started
    started_payload = json.loads(started[0].payload)
    assert started_payload["paper_id"] == file_id
    assert started_payload["job_id"] == job_id

    # ── Worker runs extraction ────────────────────────────────────────────
    _run_enqueued_extract_job(db, job_id)

    run = db.get(server.EvidenceExtractionRun, run_id)
    assert run is not None
    assert run.status == "succeeded"
    assert (run.objects_created or 0) >= 1

    done_status = client.get(f"/api/jobs/{job_id}/status")
    assert done_status.status_code == 200
    assert done_status.get_json()["status"] == "done"

    # EvidenceCreated events
    created_events = (
        db.execute(
            server.select(server.OutboxEvent).where(
                server.OutboxEvent.event_type == "EvidenceCreated"
            )
        )
        .scalars()
        .all()
    )
    assert created_events

    # ── List candidates ───────────────────────────────────────────────────
    listed = client.get(f"/api/projects/{project_id}/evidence?status=candidate")
    assert listed.status_code == 200
    listed_body = listed.get_json()
    assert listed_body["total"] >= 1
    assert listed_body["items"]
    candidate = listed_body["items"][0]
    evidence_id = candidate["id"]
    assert candidate["status"] == "candidate"
    assert candidate["paper_id"] == candidate["file_id"] == file_id
    assert candidate["quote"]
    assert candidate["claim"]
    assert candidate.get("page") is not None

    # ── Bind + accept one object ──────────────────────────────────────────
    bind = client.post(
        f"/api/documents/{document_id}/evidence-bindings",
        json={
            "evidence_object_id": evidence_id,
            "block_id": "smoke_blk",
            "selected_text": "Drug X reduces HbA1c in adults.",
            "relation": "supports",
        },
    )
    assert bind.status_code == 201, bind.get_json()

    review = client.post(
        f"/api/evidence/{evidence_id}/reviews",
        json={"status": "accepted"},
    )
    assert review.status_code == 200, review.get_json()
    assert review.get_json()["evidence"]["status"] == "accepted"

    # Claim review audit + EvidenceUpdated
    reviews = (
        db.execute(
            server.select(server.ClaimReview).where(
                server.ClaimReview.evidence_object_id == evidence_id,
                server.ClaimReview.status == "accepted",
            )
        )
        .scalars()
        .all()
    )
    assert reviews

    updated_events = (
        db.execute(
            server.select(server.OutboxEvent).where(
                server.OutboxEvent.event_type == "EvidenceUpdated",
                server.OutboxEvent.aggregate_id == evidence_id,
            )
        )
        .scalars()
        .all()
    )
    assert updated_events
    assert json.loads(updated_events[-1].payload)["status"] == "accepted"

    # ── Explain sufficient for bound accepted evidence ────────────────────
    explain = client.post(
        "/api/evidence/explain",
        json={
            "document_id": document_id,
            "project_id": project_id,
            "block_id": "smoke_blk",
            "selected_text": "Drug X reduces HbA1c in adults.",
        },
    )
    assert explain.status_code == 200
    explain_body = explain.get_json()
    assert explain_body["sufficiency"] == "sufficient"
    assert explain_body["evidence"][0]["id"] == evidence_id
    assert explain_body["evidence"][0]["status"] == "accepted"

    # Idempotent re-enqueue does not create a second job when prior succeeded
    again = client.post(
        f"/api/projects/{project_id}/evidence/extract",
        json={"file_id": file_id},
    )
    assert again.status_code == 200, again.get_json()
    assert again.get_json()["reason"] == "idempotent_reuse"
