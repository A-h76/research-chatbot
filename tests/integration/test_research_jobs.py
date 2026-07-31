"""W5/W6 integration: extract-table + async research jobs (theme_map, literature_review).

Same SQLite-safe pattern as test_evidence_smoke.py — enqueue via HTTP, invoke
worker handlers directly (no FOR UPDATE SKIP LOCKED).

Run: pytest tests/integration/test_research_jobs.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import server
import worker
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import save_analysis_result
from backend.research.jobs import RESULT_EVENT


def _medical_phase():
    return {
        "populations": [{"description": "Adults with T2DM", "confidence": 0.8}],
        "interventions": [{"name": "metformin", "confidence": 0.9}],
        "comparators": [{"name": "placebo", "is_placebo": True}],
        "outcomes": [{"name": "HbA1c at 12 weeks"}],
        "key_findings": [{"statement": "Significant HbA1c reduction"}],
        "study_characteristics": {
            "study_design": "rct",
            "number_of_arms": 2,
            "blinding": "double-blind",
            "multicenter": True,
        },
    }


@pytest.fixture
def research_world(researcher):
    """Project with Phase-1 medical extract + accepted evidence + writing doc."""
    db = researcher.db
    user = researcher.user
    project = researcher.project

    uf = server.UserFile(
        user_id=user.id,
        project_id=project.id,
        name="research-jobs.pdf",
        title="Metformin RCT",
        path=f"/tmp/research-jobs-{user.id}.pdf",
        size=200,
        meta_status="done",
        kind="document",
        content_hash=f"rj-hash-{user.id}",
        year="2024",
    )
    db.add(uf)
    db.flush()

    claims = [
        "Metformin reduces HbA1c in adults with type 2 diabetes.",
        "Placebo-controlled trials show glycemic benefit of metformin.",
        "Double-blind RCT design supports causal inference for metformin.",
    ]
    for i, claim in enumerate(claims):
        db.add(
            server.EvidenceObject(
                user_id=user.id,
                project_id=project.id,
                file_id=uf.id,
                page=2 + i,
                quote=claim,
                claim=claim,
                study_type="RCT",
                study_quality="High",
                supports_json=json.dumps(["HbA1c reduction"]),
                contradicts_json="[]",
                confidence_band="high",
                status="accepted",
                pipeline_version="2.2.0",
                content_hash=f"rj-ev-{user.id}-{i}",
                provenance_json="{}",
            )
        )

    doc = server.WritingDocument(
        user_id=user.id,
        project_id=project.id,
        title="Lit review draft",
        content="Metformin reduces HbA1c in adults with type 2 diabetes.",
        status="active",
        current_version=1,
        last_saved_hash="rj",
    )
    db.add(doc)

    save_analysis_result(
        db,
        server.AnalysisPipelineResult,
        AnalysisResult(
            file_id=uf.id,
            content_hash=uf.content_hash,
            status=AnalysisJobStatus.DONE,
            phase_results={"medical_understanding": _medical_phase()},
            pipeline_version="2.0.0",
            total_processing_time_ms=3,
        ),
        user_id=user.id,
    )
    db.commit()
    return {
        "project_id": project.id,
        "file_id": uf.id,
        "document_id": doc.id,
        "user_id": user.id,
    }


def _run_research_job(db, job_id: int, *, expected_type: str):
    """Simulate worker claim + handler for literature_review / theme_map."""
    job = db.get(server.UploadJob, job_id)
    assert job is not None
    assert job.job_type == expected_type
    assert job.status == "pending"
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    handler = worker.HANDLERS[expected_type]
    handler(db, job)

    job = db.get(server.UploadJob, job_id)
    job.status = "done"
    job.finished_at = datetime.now(timezone.utc)
    worker._mark_outbox_dispatched(db, job.id)
    db.commit()
    return job


def test_w5_structured_extract_table_json_and_csv(researcher, research_world):
    client = researcher.client
    project_id = research_world["project_id"]

    js = client.get(f"/api/projects/{project_id}/research/extract-table")
    assert js.status_code == 200, js.get_json()
    body = js.get_json()
    assert body["stage"] == "structured_extract"
    assert body["metrics"]["paper_count"] >= 1
    assert body["metrics"]["filled_rows"] >= 1
    row = body["rows"][0]
    assert row["intervention"]["value"] == "metformin"
    assert row["study_design"]["value"] == "rct"
    assert row["population"]["status"] == "known"

    csv_resp = client.get(f"/api/projects/{project_id}/research/extract-table?format=csv")
    assert csv_resp.status_code == 200
    text = csv_resp.get_data(as_text=True)
    assert "metformin" in text
    assert "population" in text.splitlines()[0]


def test_w6_theme_map_async_worker_roundtrip(researcher, research_world):
    client = researcher.client
    db = researcher.db
    project_id = research_world["project_id"]

    enqueue = client.post(
        f"/api/projects/{project_id}/research/jobs",
        json={"type": "theme_map"},
    )
    assert enqueue.status_code == 202, enqueue.get_json()
    body = enqueue.get_json()
    assert body["status"] == "queued"
    job_id = body["job_id"]
    assert isinstance(job_id, int)

    poll = client.get(f"/api/research/jobs/{job_id}")
    assert poll.status_code == 200
    assert poll.get_json()["status"] == "pending"
    assert poll.get_json()["type"] == "theme_map"

    _run_research_job(db, job_id, expected_type="theme_map")

    done = client.get(f"/api/research/jobs/{job_id}")
    assert done.status_code == 200
    done_body = done.get_json()
    assert done_body["status"] == "done"
    assert done_body["result"] is not None
    assert done_body["result"]["kind"] == "theme_map"
    assert "themes" in done_body["result"]
    assert done_body["result"]["object_count"] >= 1

    result_events = (
        db.execute(
            server.select(server.OutboxEvent).where(
                server.OutboxEvent.aggregate_type == "upload_job",
                server.OutboxEvent.aggregate_id == job_id,
                server.OutboxEvent.event_type == RESULT_EVENT,
            )
        )
        .scalars()
        .all()
    )
    assert result_events
    assert result_events[0].status == "dispatched"


def test_w6_literature_review_async_worker_roundtrip(researcher, research_world):
    client = researcher.client
    db = researcher.db
    project_id = research_world["project_id"]
    document_id = research_world["document_id"]

    enqueue = client.post(
        f"/api/projects/{project_id}/research/jobs",
        json={
            "type": "literature_review",
            "query": {
                "intent": "support_sentence",
                "section_type": "literature_review",
                "scope": {"project_id": project_id, "document_id": document_id},
                "filters": {"status": ["accepted"], "require_page_anchor": True},
                "ranking_strategy": "default_v0",
                "result_limit": 20,
                "query_text": "Metformin reduces HbA1c in adults with type 2 diabetes.",
            },
        },
    )
    assert enqueue.status_code == 202, enqueue.get_json()
    job_id = enqueue.get_json()["job_id"]
    assert isinstance(job_id, int)

    _run_research_job(db, job_id, expected_type="literature_review")

    done = client.get(f"/api/research/jobs/{job_id}")
    assert done.status_code == 200
    done_body = done.get_json()
    assert done_body["status"] == "done"
    result = done_body["result"]
    assert result is not None
    assert result["kind"] == "literature_review"
    writing = result.get("writing") or {}
    assert writing.get("status") in {"ok", "blocked"}
    # Grounded path should produce at least a writing envelope.
    assert "warnings" in writing or writing.get("sections") is not None or writing.get("paragraph") is not None


def test_w6_sync_theme_map_inline(researcher, research_world):
    client = researcher.client
    project_id = research_world["project_id"]

    resp = client.post(
        f"/api/projects/{project_id}/research/jobs",
        json={"type": "theme_map", "sync": True},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "done"
    assert body["job_id"] is None
    assert body["result"]["kind"] == "theme_map"
