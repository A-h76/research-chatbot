"""Evidence extraction → Capability Router resolve (Evolution Bite 5).

``evidence_extract`` projects Phase 1 analysis into candidate EvidenceObjects
without calling an LLM. ``resolve_evidence_extract_execution`` declares the
Research Job for inspectability; projection + persistence stay deterministic.
"""

from __future__ import annotations

from backend.ai.capability_router.resolve import resolve_execution
from backend.ai.capability_router.types import ExecutionPlan, ExecutionPolicy, ResearchJob

PROMPT_VERSION_EVIDENCE_EXTRACT = "evidence_extract@2.2"


def resolve_evidence_extract_execution(
    *,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    """Resolve Evidence Extraction Research Job plan (deterministic projector)."""
    policy = execution_policy or ExecutionPolicy.LOWEST_COST
    return resolve_execution(ResearchJob.EVIDENCE_EXTRACTION, execution_policy=policy)
