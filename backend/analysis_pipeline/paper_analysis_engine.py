"""SUE paper analysis — ACR + Gateway + AI Ledger (Bite 6)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from backend.analysis_pipeline.service import PIPELINE_VERSION as PHASE1_PIPELINE_VERSION


def invoke_paper_analysis_llm(
    *,
    ai_gateway: Any,
    model_registry: Any,
    messages: list[dict[str, Any]],
    user_id: int,
    file_id: int | None = None,
    project_id: int | None = None,
    quality_mode: str | None = None,
    confidence: float | None = None,
    response_format: Any = None,
    prompt_version_id: int | None = None,
    parent_execution_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Gateway LLM call for paper_analysis under Capability Router provenance."""
    from backend.ai.ai_ledger import AILedgerEntry, hash_output, record_execution
    from backend.ai.capability_router.paper_analysis_resolve import (
        PROMPT_VERSION_PAPER_ANALYSIS,
        resolve_paper_analysis_execution,
    )

    plan = resolve_paper_analysis_execution(quality_mode=quality_mode, confidence=confidence)
    trace_id = str(uuid.uuid4())
    started = time.perf_counter()

    call_kwargs: dict[str, Any] = {
        "model_registry": model_registry,
        "task": "paper_analysis",
        "mode": quality_mode or "balanced",
        "model": plan.model,
        "messages": messages,
        "user_id": user_id,
    }
    if confidence is not None:
        call_kwargs["confidence"] = confidence
    if response_format is not None:
        call_kwargs["response_format"] = response_format
    if prompt_version_id is not None:
        call_kwargs["prompt_version_id"] = prompt_version_id

    result = ai_gateway.call(**call_kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)

    content = (result or {}).get("content") or ""
    tin = (result or {}).get("prompt_tokens")
    tout = (result or {}).get("completion_tokens")
    tokens = int((result or {}).get("total_tokens") or 0) or None
    cost = float((result or {}).get("cost") or 0.0)

    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version=PROMPT_VERSION_PAPER_ANALYSIS,
        tokens_in=int(tin) if tin is not None else None,
        tokens_out=int(tout) if tout is not None else tokens,
        cost_usd=cost if cost else None,
        latency_ms=latency_ms,
        output_hash=hash_output(content) if content else None,
        trace_id=trace_id,
        parent_execution_id=parent_execution_id,
        status="completed",
        extra={
            "user_id": user_id,
            "file_id": file_id,
            "project_id": project_id,
            "path": "paper_analysis",
            "prompt_version_id": prompt_version_id,
        },
    )
    record_execution(entry)

    provenance = plan.to_provenance(
        tokens=tokens,
        cost_usd=cost if cost else None,
        duration_ms=latency_ms,
        prompt_version=PROMPT_VERSION_PAPER_ANALYSIS,
        execution_id=entry.execution_id,
    ).to_dict()
    return result, provenance


def record_phase1_pipeline_execution(
    *,
    file_id: int,
    user_id: int,
    project_id: int | None,
    content_hash: str,
    status: str,
    phase_keys: list[str],
    latency_ms: int,
    errors: list[str] | None = None,
) -> dict[str, Any] | None:
    """Record deterministic Phase 1 SUE pipeline completion in AI Ledger."""
    from backend.ai.ai_ledger import AILedgerEntry, hash_output, record_execution
    from backend.ai.capability_router.paper_analysis_resolve import (
        PROMPT_VERSION_PHASE1_PIPELINE,
        resolve_phase1_pipeline_execution,
    )

    plan = resolve_phase1_pipeline_execution()
    trace_id = str(uuid.uuid4())
    evaluation = {
        "validation_kind": "deterministic",
        "pipeline_version": PHASE1_PIPELINE_VERSION,
        "phase_count": len(phase_keys),
        "phases": phase_keys,
        "errors": list(errors or []),
    }
    output_hash = hash_output(
        json.dumps(
            {
                "status": status,
                "content_hash": content_hash,
                "phases": phase_keys,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )
    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version=PROMPT_VERSION_PHASE1_PIPELINE,
        latency_ms=latency_ms,
        output_hash=output_hash,
        evaluation=evaluation,
        trace_id=trace_id,
        status=status,
        extra={
            "user_id": user_id,
            "file_id": file_id,
            "project_id": project_id,
            "path": "phase1_analysis",
            "no_llm_invocation": True,
        },
    )
    record_execution(entry)
    return plan.to_provenance(
        duration_ms=latency_ms,
        prompt_version=PROMPT_VERSION_PHASE1_PIPELINE,
        execution_id=entry.execution_id,
    ).to_dict()
