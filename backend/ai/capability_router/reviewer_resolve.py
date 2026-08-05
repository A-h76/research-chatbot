"""Reviewer → Capability Router resolve (Evolution Bite 4).

Research Reviewer is **evidence-first / deterministic** (ADR-0016 § validation).
``resolve_reviewer_execution`` declares the Research Job for inspectability;
``execute_reviewer`` runs rule checks and records AI Ledger provenance without
calling the Gateway or any provider SDK.
"""

from __future__ import annotations

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    resolve_execution,
)
from backend.ai.capability_router.types import ExecutionPlan, ExecutionPolicy, ResearchJob

PROMPT_VERSION_REVIEWER = "reviewer@1.1"


def resolve_reviewer_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    """Resolve Reviewer Research Job plan (deterministic validation path)."""
    policy = execution_policy
    if policy is None:
        policy = execution_policy_from_mode(quality_mode or "balanced")
    return resolve_execution(ResearchJob.REVIEWER, execution_policy=policy)
