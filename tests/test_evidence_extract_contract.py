"""Contract tests for evidence extract and job status APIs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import save_analysis_result


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed_user_project_file(*, user_id: int, ready: bool, with_phase1: bool = False) -> dict[str, int]:
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=user_id,
                email=f"extract{user_id}@example.com",
                name=f"Extract {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"P{user_id}", emoji="E")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="paper.pdf",
            title="Paper",
            path="/tmp/paper.pdf",
            size=100,
            meta_status="done",
            kind="document",
            content_hash=f"hash-{user_id}",
        )
        db.add(uf)
        db.flush()
        if ready:
            db.add(
                server.Chunk(
                    file_id=uf.id,
                    idx=0,
                    content="Chunk for research ready state.",
                    page=1,
                    section="abstract",
                )
            )
        if with_phase1:
            save_analysis_result(
                db,
                server.AnalysisPipelineResult,
                AnalysisResult(
                    file_id=uf.id,
                    content_hash=f"hash-{user_id}",
                    status=AnalysisJobStatus.DONE,
                    phase_results={
                        "knowledge_graph": {
                            "version": "1.0.0",
                            "nodes": [
                                {
                                    "node_id": f"claim-{user_id}",
                                    "node_type": "evidence_claim",
                                    "label": "Drug X improves outcome",
                                    "evidence_references": [
                                        {
                                            "page": 1,
                                            "section": "results",
                                            "text_snippet": "Drug X improved the primary outcome.",
                                            "character_range": [10, 50],
                                        }
                                    ],
                                }
                            ],
                            "edges": [],
                        },
                        "evidence_grading": {"pipeline_version": "1.0.0"},
                    },
                    pipeline_version="2.0.0",
                    total_processing_time_ms=10,
                ),
                user_id=user_id,
            )
        db.commit()
        return {"project_id": project.id, "file_id": uf.id}
    finally:
        db.close()


def test_extract_returns_400_when_not_research_ready():
    seeded = _seed_user_project_file(user_id=6101, ready=False)
    client = _client()
    _login(client, 6101)

    resp = client.post(
        f"/api/projects/{seeded['project_id']}/evidence/extract",
        json={"file_id": seeded["file_id"]},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "not_research_ready"
    assert body["reason"] == "not_research_ready"
    assert body["status"] == "skipped"


def test_extract_returns_409_when_missing_phase1():
    seeded = _seed_user_project_file(user_id=6104, ready=True, with_phase1=False)
    client = _client()
    _login(client, 6104)
    resp = client.post(
        f"/api/projects/{seeded['project_id']}/evidence/extract",
        json={"file_id": seeded["file_id"]},
    )
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "missing_phase1"
    assert body["status"] == "skipped"


def test_extract_enqueues_async_202():
    seeded = _seed_user_project_file(user_id=6105, ready=True, with_phase1=True)
    client = _client()
    _login(client, 6105)
    resp = client.post(
        f"/api/projects/{seeded['project_id']}/evidence/extract",
        json={"file_id": seeded["file_id"]},
    )
    assert resp.status_code == 202, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "pending"
    assert isinstance(body["job_id"], int)
    assert isinstance(body["run_id"], int)
    assert body["pipeline_version"]

    db = server.SessionLocal()
    try:
        job = db.get(server.UploadJob, body["job_id"])
        run = db.get(server.EvidenceExtractionRun, body["run_id"])
        assert job is not None
        assert job.job_type == "evidence_extract"
        assert job.status == "pending"
        assert run is not None
        assert run.status == "queued"
        assert run.job_id == job.id
        events = (
            db.execute(
                server.select(server.OutboxEvent).where(
                    server.OutboxEvent.aggregate_id.in_((job.id, run.id)),
                )
            )
            .scalars()
            .all()
        )
        job_events = [e for e in events if e.aggregate_type == "upload_job"]
        started_events = [e for e in events if e.event_type == "EvidenceExtractionStarted"]
        assert len(job_events) == 1
        assert len(started_events) == 1
        payload = json.loads(job_events[0].payload)
        assert payload["already_applied"] is False
        assert payload["project_id"] == seeded["project_id"]
        assert payload["run_id"] == run.id
        started_payload = json.loads(started_events[0].payload)
        assert started_payload["run_id"] == run.id
        assert started_payload["paper_id"] == seeded["file_id"]
        assert started_payload["job_id"] == job.id
    finally:
        db.close()


def test_extract_already_running_returns_409():
    seeded = _seed_user_project_file(user_id=6106, ready=True, with_phase1=True)
    db = server.SessionLocal()
    try:
        job = server.UploadJob(
            user_id=6106,
            file_id=seeded["file_id"],
            job_type="evidence_extract",
            status="running",
        )
        db.add(job)
        db.commit()
    finally:
        db.close()

    client = _client()
    _login(client, 6106)
    resp = client.post(
        f"/api/projects/{seeded['project_id']}/evidence/extract",
        json={"file_id": seeded["file_id"]},
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_running"


def test_extract_sync_emits_evidence_created_event():
    seeded = _seed_user_project_file(user_id=6107, ready=True, with_phase1=True)
    client = _client()
    _login(client, 6107)
    resp = client.post(
        f"/api/projects/{seeded['project_id']}/evidence/extract",
        json={"file_id": seeded["file_id"], "sync": True},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "succeeded"
    assert body["objects_created"] >= 1

    db = server.SessionLocal()
    try:
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
        payload = json.loads(created_events[-1].payload)
        assert payload["project_id"] == seeded["project_id"]
        assert payload["paper_id"] == seeded["file_id"]
        assert payload["status"] == "candidate"
    finally:
        db.close()


def test_job_status_includes_job_type_attempts_last_error():
    db = server.SessionLocal()
    try:
        uid = 6102
        db.add(
            server.User(
                id=uid,
                email=f"jobs{uid}@example.com",
                name=f"Jobs {uid}",
                created_at=datetime.now(timezone.utc),
            )
        )
        job = server.UploadJob(
            user_id=uid,
            file_id=None,
            job_type="evidence_extract",
            status="failed",
            attempts=2,
            last_error="missing_phase1",
        )
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    client = _client()
    _login(client, uid)
    resp = client.get(f"/api/jobs/{job_id}/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["job_type"] == "evidence_extract"
    assert body["attempts"] == 2
    assert body["last_error"] == "missing_phase1"
    assert body["lifecycle"] == "dead_letter"
    assert body["retry"]["will_retry"] is False
    assert body["error"]["code"] == "missing_phase1"
    assert body["max_attempts"] >= 1


def test_review_emits_evidence_updated_event():
    seeded = _seed_user_project_file(user_id=6108, ready=True, with_phase1=True)
    client = _client()
    _login(client, 6108)
    sync_resp = client.post(
        f"/api/projects/{seeded['project_id']}/evidence/extract",
        json={"file_id": seeded["file_id"], "sync": True},
    )
    assert sync_resp.status_code == 200

    db = server.SessionLocal()
    try:
        ev = (
            db.execute(
                server.select(server.EvidenceObject).where(
                    server.EvidenceObject.user_id == 6108,
                    server.EvidenceObject.project_id == seeded["project_id"],
                    server.EvidenceObject.file_id == seeded["file_id"],
                    server.EvidenceObject.status == "candidate",
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        evidence_id = ev.id
    finally:
        db.close()

    review_resp = client.post(f"/api/evidence/{evidence_id}/reviews", json={"status": "accepted"})
    assert review_resp.status_code == 200, review_resp.get_json()

    db = server.SessionLocal()
    try:
        updated_events = (
            db.execute(
                server.select(server.OutboxEvent).where(
                    server.OutboxEvent.event_type == "EvidenceUpdated"
                )
            )
            .scalars()
            .all()
        )
        assert updated_events
        payload = json.loads(updated_events[-1].payload)
        assert payload["evidence_object_id"] == evidence_id
        assert payload["status"] == "accepted"
    finally:
        db.close()


def test_list_evidence_pagination_envelope():
    seeded = _seed_user_project_file(user_id=6103, ready=True)
    db = server.SessionLocal()
    try:
        for i in range(3):
            db.add(
                server.EvidenceObject(
                    user_id=6103,
                    project_id=seeded["project_id"],
                    file_id=seeded["file_id"],
                    page=i + 1,
                    quote=f"quote {i}",
                    claim=f"claim {i}",
                    confidence_band="moderate",
                    status="candidate",
                    pipeline_version="2.2.0",
                    content_hash=f"list-hash-{i}",
                    provenance_json="{}",
                )
            )
        db.commit()
    finally:
        db.close()

    client = _client()
    _login(client, 6103)
    resp = client.get(
        f"/api/projects/{seeded['project_id']}/evidence?limit=2&offset=0"
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    assert body["items"][0]["paper_id"] == body["items"][0]["file_id"]


def test_binding_create_and_delete_emit_contract_events():
    seeded = _seed_user_project_file(user_id=6109, ready=True, with_phase1=True)
    db = server.SessionLocal()
    try:
        doc = server.WritingDocument(
            user_id=6109,
            project_id=seeded["project_id"],
            title="Draft",
            content="Drug X improves outcome in adults.",
            status="active",
            current_version=1,
            last_saved_hash="h",
        )
        db.add(doc)
        ev = server.EvidenceObject(
            user_id=6109,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            page=1,
            quote="Drug X improved the primary outcome.",
            claim="Drug X improves outcome",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash="bind-hash-6109",
            provenance_json="{}",
        )
        db.add(ev)
        db.commit()
        document_id = doc.id
        evidence_id = ev.id
    finally:
        db.close()

    client = _client()
    _login(client, 6109)
    create_resp = client.post(
        f"/api/documents/{document_id}/evidence-bindings",
        json={
            "evidence_object_id": evidence_id,
            "block_id": "blk_bind",
            "selected_text": "Drug X improves outcome in adults.",
            "relation": "supports",
        },
    )
    assert create_resp.status_code == 201, create_resp.get_json()
    binding_id = create_resp.get_json()["id"]

    db = server.SessionLocal()
    try:
        created = (
            db.execute(
                server.select(server.OutboxEvent).where(
                    server.OutboxEvent.event_type == "BindingCreated",
                    server.OutboxEvent.aggregate_id == binding_id,
                )
            )
            .scalars()
            .all()
        )
        assert len(created) == 1
        payload = json.loads(created[0].payload)
        assert payload == {
            "binding_id": binding_id,
            "document_id": document_id,
            "evidence_object_id": evidence_id,
        }
    finally:
        db.close()

    delete_resp = client.delete(f"/api/evidence-bindings/{binding_id}")
    assert delete_resp.status_code == 200

    db = server.SessionLocal()
    try:
        deleted = (
            db.execute(
                server.select(server.OutboxEvent).where(
                    server.OutboxEvent.event_type == "BindingDeleted",
                    server.OutboxEvent.aggregate_id == binding_id,
                )
            )
            .scalars()
            .all()
        )
        assert len(deleted) == 1
        payload = json.loads(deleted[0].payload)
        assert payload == {
            "binding_id": binding_id,
            "document_id": document_id,
            "evidence_object_id": evidence_id,
        }
        assert db.get(server.WritingSentenceBinding, binding_id) is None
    finally:
        db.close()
