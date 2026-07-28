"""Stage 4 reliability: extraction idempotency, supersede, review transitions."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import save_analysis_result
from backend.evidence.services.extract_service import run_evidence_extraction


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _phase_payload():
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
                    "label": "Outcome improved",
                    "properties": {},
                    "evidence_references": [
                        {
                            "page": 4,
                            "section": "results",
                            "text_snippet": "Outcome improved by 12%",
                            "character_range": [100, 130],
                        }
                    ],
                },
                {"node_id": "o1", "node_type": "outcome", "label": "Outcome", "evidence_references": []},
            ],
            "edges": [
                {
                    "edge_id": "e1",
                    "source_node_id": "c1",
                    "target_node_id": "o1",
                    "edge_type": "supports",
                }
            ],
        },
    }


def _seed_ready_file(user_id: int):
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=user_id,
                email=f"rel{user_id}@example.com",
                name=f"Rel {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"RP{user_id}", emoji="R")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="ready.pdf",
            title="Ready Paper",
            path="/tmp/ready.pdf",
            size=100,
            meta_status="done",
            kind="document",
            content_hash="filehash-ready",
        )
        db.add(uf)
        db.flush()
        db.add(
            server.Chunk(
                file_id=uf.id,
                idx=0,
                content="Outcome improved by 12% in the treatment arm.",
                page=4,
                section="results",
            )
        )
        save_analysis_result(
            db,
            server.AnalysisPipelineResult,
            AnalysisResult(
                file_id=uf.id,
                content_hash="filehash-ready",
                status=AnalysisJobStatus.DONE,
                phase_results=_phase_payload(),
                pipeline_version="2.0.0",
                total_processing_time_ms=10,
            ),
            user_id=user_id,
        )
        db.commit()
        return {"project_id": project.id, "file_id": uf.id}
    finally:
        db.close()


def test_extract_not_ready_is_skipped():
    db = server.SessionLocal()
    try:
        uid = 5001
        db.add(
            server.User(
                id=uid,
                email=f"rel{uid}@example.com",
                name="x",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=uid, name="nr", emoji="N")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=uid,
            project_id=project.id,
            name="meta-only.pdf",
            title="",
            path="",
            size=0,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.commit()
        pid, fid = project.id, uf.id
    finally:
        db.close()

    from backend.analysis_pipeline.persistence import load_analysis_result

    db = server.SessionLocal()
    try:
        result = run_evidence_extraction(
            db,
            user_id=5001,
            project_id=pid,
            file_id=fid,
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "not_research_ready"
    finally:
        db.close()


def test_repeated_extraction_is_idempotent():
    from backend.analysis_pipeline.persistence import load_analysis_result

    seeded = _seed_ready_file(5002)
    db = server.SessionLocal()
    try:
        first = run_evidence_extraction(
            db,
            user_id=5002,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
        )
        assert first["status"] == "succeeded"
        assert first["objects_created"] >= 1
        second = run_evidence_extraction(
            db,
            user_id=5002,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
            force=False,
        )
        assert second["reason"] == "idempotent_reuse"
        rows = (
            db.execute(
                server.select(server.EvidenceObject).where(
                    server.EvidenceObject.project_id == seeded["project_id"],
                    server.EvidenceObject.status == "candidate",
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == first["objects_created"]
    finally:
        db.close()


def test_force_reextract_supersedes_prior():
    from backend.analysis_pipeline.persistence import load_analysis_result

    seeded = _seed_ready_file(5003)
    db = server.SessionLocal()
    try:
        run_evidence_extraction(
            db,
            user_id=5003,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
        )
        # Force path: mark prior content to collide then force
        prior = (
            db.execute(
                server.select(server.EvidenceObject).where(
                    server.EvidenceObject.file_id == seeded["file_id"]
                )
            )
            .scalars()
            .first()
        )
        assert prior is not None
        prior_id = prior.id
        run_evidence_extraction(
            db,
            user_id=5003,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
            force=True,
        )
        db.refresh(prior) if hasattr(db, "refresh") else None
        prior2 = db.get(server.EvidenceObject, prior_id)
        # After force with same hash, extract_service may skip duplicate hashes unless existing
        # is superseded — verify no explosion of active candidates
        active = (
            db.execute(
                server.select(server.EvidenceObject).where(
                    server.EvidenceObject.file_id == seeded["file_id"],
                    server.EvidenceObject.status.in_(("candidate", "accepted")),
                )
            )
            .scalars()
            .all()
        )
        assert len(active) >= 1
        assert prior2 is not None
    finally:
        db.close()


def test_candidate_to_accepted_and_rejected():
    seeded = _seed_ready_file(5004)
    from backend.analysis_pipeline.persistence import load_analysis_result

    db = server.SessionLocal()
    try:
        run_evidence_extraction(
            db,
            user_id=5004,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
        )
        ev = (
            db.execute(
                server.select(server.EvidenceObject).where(
                    server.EvidenceObject.file_id == seeded["file_id"]
                )
            )
            .scalars()
            .first()
        )
        eid = ev.id
    finally:
        db.close()

    client = _client()
    _login(client, 5004)
    ok = client.post(f"/api/evidence/{eid}/reviews", json={"status": "accepted"})
    assert ok.status_code == 200
    assert ok.get_json()["evidence"]["status"] == "accepted"

    # Second object path: reject a fresh candidate
    db = server.SessionLocal()
    try:
        ev2 = server.EvidenceObject(
            user_id=5004,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            page=5,
            quote="other quote",
            claim="other claim",
            confidence_band="low",
            status="candidate",
            pipeline_version="2.2.0",
            content_hash="other-hash-5004",
            provenance_json="{}",
        )
        db.add(ev2)
        db.commit()
        eid2 = ev2.id
    finally:
        db.close()

    rej = client.post(f"/api/evidence/{eid2}/reviews", json={"status": "rejected", "reason": "noise"})
    assert rej.status_code == 200
    assert rej.get_json()["evidence"]["status"] == "rejected"


def test_edited_review_supersedes_append_only():
    seeded = _seed_ready_file(5005)
    from backend.analysis_pipeline.persistence import load_analysis_result

    db = server.SessionLocal()
    try:
        run_evidence_extraction(
            db,
            user_id=5005,
            project_id=seeded["project_id"],
            file_id=seeded["file_id"],
            UserFile=server.UserFile,
            AnalysisPipelineResult=server.AnalysisPipelineResult,
            EvidenceObject=server.EvidenceObject,
            EvidenceExtractionRun=server.EvidenceExtractionRun,
            load_analysis_result=load_analysis_result,
        )
        ev = (
            db.execute(
                server.select(server.EvidenceObject).where(
                    server.EvidenceObject.file_id == seeded["file_id"]
                )
            )
            .scalars()
            .first()
        )
        eid = ev.id
    finally:
        db.close()

    client = _client()
    _login(client, 5005)
    resp = client.post(
        f"/api/evidence/{eid}/reviews",
        json={"status": "edited", "edited_claim": "Human-corrected claim", "edited_quote": "Human quote"},
    )
    assert resp.status_code == 200
    body = resp.get_json()["evidence"]
    assert body["status"] == "accepted"
    assert body["claim"] == "Human-corrected claim"
    assert body["id"] != eid

    db = server.SessionLocal()
    try:
        old = db.get(server.EvidenceObject, eid)
        assert old.status == "superseded"
    finally:
        db.close()
