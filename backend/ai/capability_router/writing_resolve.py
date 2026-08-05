"""Writing Assistant → Capability Router resolve (Evolution Bite 3).

``POST /api/writing`` text transforms route through ``resolve_execution``
for ``ResearchJob.WRITING`` (ADR-0016). Action-specific policies pick
economy vs quality without exposing model brands in the UI.
"""

from __future__ import annotations

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    resolve_execution,
)
from backend.ai.capability_router.types import ExecutionPlan, ExecutionPolicy, ResearchJob

PROMPT_VERSION_WRITING_ASSISTANT = "writing_assistant@1.0"

_ACTION_POLICIES: dict[str, ExecutionPolicy] = {
    "improve_grammar": ExecutionPolicy.FASTEST,
    "shorten": ExecutionPolicy.FASTEST,
    "rewrite_academic": ExecutionPolicy.BALANCED,
    "improve_clarity": ExecutionPolicy.BALANCED,
    "expand": ExecutionPolicy.BALANCED,
    "generate_abstract": ExecutionPolicy.HIGHEST_QUALITY,
    "improve_conclusion": ExecutionPolicy.BALANCED,
}


def resolve_writing_assistant_execution(
    *,
    action: str,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    """Resolve a Writing Assistant Research Job plan for one transform action."""
    policy = execution_policy
    if policy is None:
        if quality_mode:
            policy = execution_policy_from_mode(quality_mode)
        else:
            policy = _ACTION_POLICIES.get((action or "").strip(), ExecutionPolicy.BALANCED)
    return resolve_execution(ResearchJob.WRITING, execution_policy=policy)
