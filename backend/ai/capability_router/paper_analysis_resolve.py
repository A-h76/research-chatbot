"""Paper analysis (SUE LLM) → Capability Router resolve (Evolution Bite 6)."""

from __future__ import annotations

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    resolve_execution,
)
from backend.ai.capability_router.types import ExecutionPlan, ExecutionPolicy, ResearchJob

PROMPT_VERSION_PAPER_ANALYSIS = "paper_analysis@1.0"
PROMPT_VERSION_PHASE1_PIPELINE = "phase1_pipeline@2.0"


def resolve_paper_analysis_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
    confidence: float | None = None,
) -> ExecutionPlan:
    """Resolve Analyze Paper Research Job for the SUE LLM overview call."""
    policy = execution_policy
    if policy is None:
        policy = execution_policy_from_mode(quality_mode or "balanced")
    return resolve_execution(ResearchJob.ANALYZE_PAPER, execution_policy=policy)


def resolve_phase1_pipeline_execution() -> ExecutionPlan:
    """Resolve Analyze Paper job for deterministic Phase 1 pipeline (no LLM)."""
    return resolve_execution(
        ResearchJob.ANALYZE_PAPER,
        execution_policy=ExecutionPolicy.BALANCED,
    )
