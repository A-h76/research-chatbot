"""Persist extraction runs and candidate EvidenceObjects (factory deps)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from backend.evidence.api.errors import ErrorCode, EvidenceDomainError
from backend.evidence.phase_projector import candidates_from_phase_results
from backend.evidence.provenance import compute_input_content_hash, provenance_to_json
from backend.evidence.services.logging import log_evidence_metric
from backend.library.readiness import research_readiness

PIPELINE_VERSION = "2.2.0"


def run_evidence_extraction(
    db,
    *,
    user_id: int,
    project_id: int,
    file_id: int,
    UserFile: Any,
    AnalysisPipelineResult: Any,
    EvidenceObject: Any,
    EvidenceExtractionRun: Any,
    load_analysis_result: Callable,
    force: bool = False,
    pipeline_version: str = PIPELINE_VERSION,
    job_id: int | None = None,
    OutboxEvent: Any | None = None,
) -> dict[str, Any]:
    def _emit_event(*, aggregate_type: str, aggregate_id: int, event_type: str, payload: dict[str, Any]) -> None:
        if OutboxEvent is None:
            return
        db.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=int(aggregate_id),
                event_type=event_type,
                payload=json.dumps(payload, ensure_ascii=False),
                status="dispatched",
                dispatched_at=datetime.now(timezone.utc),
            )
        )

    uf = db.get(UserFile, int(file_id))
    if not uf or int(uf.user_id) != int(user_id):
        raise EvidenceDomainError(ErrorCode.NOT_FOUND, "file_not_found")

    readiness = research_readiness(uf)
    if readiness != "research_ready":
        run = EvidenceExtractionRun(
            user_id=user_id,
            project_id=project_id,
            file_id=file_id,
            pipeline_version=pipeline_version,
            input_content_hash="not_ready",
            status="skipped",
            objects_created=0,
            error_json=json.dumps({"reason": "not_research_ready", "readiness": readiness}),
            job_id=job_id,
            finished_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        return {"status": "skipped", "reason": "not_research_ready", "objects_created": 0, "run_id": run.id}

    analysis = load_analysis_result(db, AnalysisPipelineResult, file_id)
    if not analysis or not analysis.phase_results:
        run = EvidenceExtractionRun(
            user_id=user_id,
            project_id=project_id,
            file_id=file_id,
            pipeline_version=pipeline_version,
            input_content_hash="missing_phase1",
            status="skipped",
            objects_created=0,
            error_json=json.dumps({"reason": "missing_phase1"}),
            job_id=job_id,
            finished_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        return {"status": "skipped", "reason": "missing_phase1", "objects_created": 0, "run_id": run.id}

    file_fp = analysis.content_hash or getattr(uf, "content_hash", "") or f"file:{file_id}"
    input_hash = compute_input_content_hash(
        file_fingerprint=file_fp,
        document_understanding_version=str(
            (analysis.phase_results.get("document_understanding") or {}).get("pipeline_version") or ""
        ),
        evidence_grading_version=str(
            (analysis.phase_results.get("evidence_grading") or {}).get("pipeline_version") or ""
        ),
        knowledge_graph_version=str(
            (analysis.phase_results.get("knowledge_graph") or {}).get("pipeline_version")
            or (analysis.phase_results.get("knowledge_graph") or {}).get("version")
            or ""
        ),
        extraction_prompt_version="phase_projector.v1",
        pipeline_version=pipeline_version,
    )

    from sqlalchemy import select

    prior = db.execute(
        select(EvidenceExtractionRun).where(
            EvidenceExtractionRun.project_id == project_id,
            EvidenceExtractionRun.file_id == file_id,
            EvidenceExtractionRun.pipeline_version == pipeline_version,
            EvidenceExtractionRun.input_content_hash == input_hash,
            EvidenceExtractionRun.status == "succeeded",
        )
    ).scalar_one_or_none()
    if prior and not force:
        return {
            "status": "succeeded",
            "reason": "idempotent_reuse",
            "objects_created": prior.objects_created or 0,
            "run_id": prior.id,
        }

    queued_run = None
    if job_id is not None:
        queued_run = db.execute(
            select(EvidenceExtractionRun).where(
                EvidenceExtractionRun.job_id == int(job_id),
                EvidenceExtractionRun.project_id == project_id,
                EvidenceExtractionRun.file_id == file_id,
                EvidenceExtractionRun.pipeline_version == pipeline_version,
            )
        ).scalar_one_or_none()

    if queued_run is not None:
        run = queued_run
        run.status = "running"
        run.objects_created = 0
        run.error_json = "{}"
        run.finished_at = None
    elif prior and force:
        run = prior
        run.status = "running"
        run.objects_created = 0
        run.error_json = "{}"
        run.job_id = job_id
        run.finished_at = None
    else:
        run = EvidenceExtractionRun(
            user_id=user_id,
            project_id=project_id,
            file_id=file_id,
            pipeline_version=pipeline_version,
            input_content_hash=input_hash,
            status="running",
            objects_created=0,
            job_id=job_id,
        )
        db.add(run)
    db.flush()

    candidates = candidates_from_phase_results(
        file_id=file_id,
        phase_results=analysis.phase_results,
        pipeline_version=pipeline_version,
    )

    # Supersede prior active objects for this file+project under older hashes
    prior_active = (
        db.execute(
            select(EvidenceObject).where(
                EvidenceObject.project_id == project_id,
                EvidenceObject.file_id == file_id,
                EvidenceObject.status.in_(("candidate", "accepted")),
            )
        )
        .scalars()
        .all()
    )
    prior_by_hash = {p.content_hash: p for p in prior_active}

    created = 0
    for cand in candidates:
        existing = prior_by_hash.get(cand.content_hash)
        if existing and existing.pipeline_version == pipeline_version and not force:
            continue
        if existing:
            existing.status = "superseded"
            existing.updated_at = datetime.now(timezone.utc)

        row = EvidenceObject(
            user_id=user_id,
            project_id=project_id,
            file_id=file_id,
            page=cand.page,
            char_start=cand.char_start,
            char_end=cand.char_end,
            section=cand.section,
            quote=cand.quote,
            claim=cand.claim,
            study_type=cand.study_type,
            study_quality=cand.study_quality,
            supports_json=json.dumps(cand.supports, ensure_ascii=False),
            contradicts_json=json.dumps(cand.contradicts, ensure_ascii=False),
            limitations_json=json.dumps(cand.limitations, ensure_ascii=False),
            confidence_band=cand.confidence_band,
            status="candidate",
            pipeline_version=pipeline_version,
            created_by="analysis-pipeline",
            content_hash=cand.content_hash,
            supersedes_id=existing.id if existing else None,
            provenance_json=provenance_to_json(cand.provenance),
            source_kg_node_id=cand.source_kg_node_id,
        )
        db.add(row)
        db.flush()
        _emit_event(
            aggregate_type="evidence_object",
            aggregate_id=row.id,
            event_type="EvidenceCreated",
            payload={
                "evidence_object_id": row.id,
                "project_id": project_id,
                "paper_id": file_id,
                "status": "candidate",
            },
        )
        created += 1

    run.status = "succeeded"
    run.objects_created = created
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    log_evidence_metric(
        "extraction_completed",
        user_id=user_id,
        project_id=project_id,
        file_id=file_id,
        objects_created=created,
        pipeline_version=pipeline_version,
    )
    return {"status": "succeeded", "reason": "extracted", "objects_created": created, "run_id": run.id}
