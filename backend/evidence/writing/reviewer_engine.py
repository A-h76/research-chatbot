"""ACR-wrapped Research Reviewer — deterministic validation + ledger (Bite 4)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from backend.evidence.writing.reviewer import REVIEWER_VERSION, review_grounded_draft


def execute_reviewer(
    *,
    sections: list[dict[str, Any]],
    consensus: dict[str, Any] | None = None,
    conflict: dict[str, Any] | None = None,
    supporting_count: int | None = None,
    user_id: int | None = None,
    project_id: int | None = None,
    document_id: int | None = None,
    parent_execution_id: str | None = None,
    quality_mode: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Run rule-based reviewer under Capability Router provenance.

    Returns ``(review_dict, provenance_dict_or_none)``. Never invokes LLM.
    """
    from backend.ai.ai_ledger import AILedgerEntry, hash_output, record_execution
    from backend.ai.capability_router.reviewer_resolve import (
        PROMPT_VERSION_REVIEWER,
        resolve_reviewer_execution,
    )

    plan = resolve_reviewer_execution(quality_mode=quality_mode)
    trace_id = str(uuid.uuid4())
    started = time.perf_counter()

    review = review_grounded_draft(
        sections=sections,
        consensus=consensus,
        conflict=conflict,
        supporting_count=supporting_count,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    metrics = dict(review.get("metrics") or {})
    evaluation = {
        "validation_kind": "deterministic",
        "reviewer_version": REVIEWER_VERSION,
        "status": review.get("status"),
        "pass_rate": review.get("pass_rate"),
        "issue_count": review.get("issue_count"),
        "grounding_pct": metrics.get("grounding_pct"),
        "citation_coverage_pct": metrics.get("citation_coverage_pct"),
        "unsupported_claims": metrics.get("unsupported_claims"),
    }
    output_hash = hash_output(
        json.dumps(
            {
                "status": review.get("status"),
                "pass_rate": review.get("pass_rate"),
                "issue_count": review.get("issue_count"),
                "metrics": metrics,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )

    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version=PROMPT_VERSION_REVIEWER,
        evidence_source_ids=[
            str(eid)
            for sec in sections
            for eid in (sec.get("evidence_ids") or [])
            if eid is not None
        ],
        latency_ms=latency_ms,
        output_hash=output_hash,
        evaluation=evaluation,
        trace_id=trace_id,
        parent_execution_id=parent_execution_id,
        status=str(review.get("status") or "completed"),
        extra={
            "user_id": user_id,
            "project_id": project_id,
            "document_id": document_id,
            "path": "research_reviewer",
            "validation_kind": "deterministic",
            "no_llm_invocation": True,
        },
    )
    record_execution(entry)

    provenance = plan.to_provenance(
        duration_ms=latency_ms,
        prompt_version=PROMPT_VERSION_REVIEWER,
        execution_id=entry.execution_id,
    ).to_dict()
    if provenance.get("ai_execution"):
        provenance["ai_execution"]["extra"] = {
            "validation_kind": "deterministic",
            "reviewer_version": REVIEWER_VERSION,
        }

    review = dict(review)
    review["ai_execution"] = provenance.get("ai_execution") or provenance
    return review, provenance
