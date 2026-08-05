"""Search RAG — ACR + Gateway + AI Ledger (Bite 7)."""

from __future__ import annotations

import time
import uuid
from typing import Any


def invoke_rag_llm(
    *,
    ai_gateway: Any,
    model_registry: Any,
    messages: list[dict[str, Any]],
    user_id: int,
    quality_mode: str | None = None,
    confidence: float | None = None,
    prompt_version_id: int | None = None,
    project_id: int | None = None,
    file_id: int | None = None,
    source_chunk_ids: list[int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Gateway LLM call for semantic search RAG under Capability Router provenance."""
    from backend.ai.ai_ledger import AILedgerEntry, hash_output
    from backend.ai.ledger_facade import record_acr_execution
    from backend.ai.capability_router.search_resolve import (
        PROMPT_VERSION_RAG,
        resolve_search_execution,
    )

    plan = resolve_search_execution(quality_mode=quality_mode, confidence=confidence)
    trace_id = str(uuid.uuid4())
    started = time.perf_counter()

    call_kwargs: dict[str, Any] = {
        "model_registry": model_registry,
        "task": "rag",
        "mode": quality_mode or "balanced",
        "model": plan.model,
        "messages": messages,
        "user_id": user_id,
    }
    if confidence is not None:
        call_kwargs["confidence"] = confidence
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
        prompt_version=PROMPT_VERSION_RAG,
        tools_used=["semantic_search"],
        evidence_source_ids=[str(cid) for cid in (source_chunk_ids or [])],
        tokens_in=int(tin) if tin is not None else None,
        tokens_out=int(tout) if tout is not None else tokens,
        cost_usd=cost if cost else None,
        latency_ms=latency_ms,
        output_hash=hash_output(content) if content else None,
        trace_id=trace_id,
        status="completed",
        extra={
            "user_id": user_id,
            "project_id": project_id,
            "file_id": file_id,
            "path": "api_rag",
            "source_count": len(source_chunk_ids or []),
        },
    )
    record_acr_execution(
        entry,
        model_registry=model_registry,
        user_id=user_id,
        cost_action="chat",
        prompt_version_id=prompt_version_id,
    )

    provenance = plan.to_provenance(
        tokens=tokens,
        cost_usd=cost if cost else None,
        duration_ms=latency_ms,
        prompt_version=PROMPT_VERSION_RAG,
        execution_id=entry.execution_id,
    ).to_dict()
    return result, provenance
