"""Search / RAG → Capability Router resolve (Evolution Bite 7)."""

from __future__ import annotations

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    resolve_execution,
)
from backend.ai.capability_router.types import ExecutionPlan, ExecutionPolicy, ResearchJob

PROMPT_VERSION_RAG = "semantic_search@1.0"


def resolve_search_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
    confidence: float | None = None,
) -> ExecutionPlan:
    """Resolve Search Research Job plan for RAG answer generation."""
    policy = execution_policy
    if policy is None:
        policy = execution_policy_from_mode(quality_mode or "balanced")
    return resolve_execution(ResearchJob.SEARCH, execution_policy=policy)
