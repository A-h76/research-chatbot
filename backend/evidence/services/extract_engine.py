"""ACR-wrapped evidence extraction — deterministic projection + ledger (Bite 5)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Callable

from backend.evidence.phase_projector import EXTRACTION_PROMPT_VERSION
from backend.evidence.services.extract_service import PIPELINE_VERSION, run_evidence_extraction


def execute_evidence_extraction(
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
    parent_execution_id: str | None = None,
) -> dict[str, Any]:
    """Run evidence extraction under Capability Router provenance.

    Wraps ``run_evidence_extraction`` (no LLM). Records AI Ledger on every
    terminal outcome (succeeded / skipped / idempotent_reuse).
    """
    from backend.ai.ai_ledger import AILedgerEntry, hash_output, record_execution
    from backend.ai.capability_router.evidence_extract_resolve import (
        PROMPT_VERSION_EVIDENCE_EXTRACT,
        resolve_evidence_extract_execution,
    )

    plan = resolve_evidence_extract_execution()
    trace_id = str(uuid.uuid4())
    started = time.perf_counter()

    result = run_evidence_extraction(
        db,
        user_id=user_id,
        project_id=project_id,
        file_id=file_id,
        UserFile=UserFile,
        AnalysisPipelineResult=AnalysisPipelineResult,
        EvidenceObject=EvidenceObject,
        EvidenceExtractionRun=EvidenceExtractionRun,
        load_analysis_result=load_analysis_result,
        force=force,
        pipeline_version=pipeline_version,
        job_id=job_id,
        OutboxEvent=OutboxEvent,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    status = str(result.get("status") or "unknown")
    objects_created = int(result.get("objects_created") or 0)
    reason = str(result.get("reason") or "")
    evaluation = {
        "validation_kind": "deterministic",
        "objects_created": objects_created,
        "reason": reason,
        "pipeline_version": pipeline_version,
        "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
    }
    output_hash = hash_output(
        json.dumps(
            {
                "status": status,
                "reason": reason,
                "objects_created": objects_created,
                "run_id": result.get("run_id"),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )

    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version=PROMPT_VERSION_EVIDENCE_EXTRACT,
        latency_ms=latency_ms,
        output_hash=output_hash,
        evaluation=evaluation,
        trace_id=trace_id,
        parent_execution_id=parent_execution_id,
        status=status,
        extra={
            "user_id": user_id,
            "project_id": project_id,
            "file_id": file_id,
            "path": "evidence_extract",
            "job_id": job_id,
            "no_llm_invocation": True,
        },
    )
    record_execution(entry)

    provenance = plan.to_provenance(
        duration_ms=latency_ms,
        prompt_version=PROMPT_VERSION_EVIDENCE_EXTRACT,
        execution_id=entry.execution_id,
    ).to_dict()
    if provenance.get("ai_execution"):
        provenance["ai_execution"]["extra"] = {
            "validation_kind": "deterministic",
            "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
        }

    result = dict(result)
    result["ai_execution"] = provenance.get("ai_execution") or provenance
    return result
