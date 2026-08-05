"""Chat → Capability Router resolve (Evolution Tracker: AI Invocation).

``/api/chat`` keeps OpenAI Responses streaming transport, but **model authority**
goes through ``resolve_execution(ResearchJob.CHAT)`` (ADR-0016). Optional
allowlisted client/conversation models become ``model_override`` so threads
stay stable without letting product UX invent unrouted brands.
"""

from __future__ import annotations

from collections.abc import Collection

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    resolve_execution,
)
from backend.ai.capability_router.types import ExecutionPlan, ResearchJob

PROMPT_VERSION_CHAT = "chat@1.0"


def resolve_chat_execution(
    *,
    requested_model: str | None = None,
    conversation_model: str | None = None,
    allowlisted_models: Collection[str] | None = None,
    quality_mode: str | None = None,
    execution_policy: str | None = None,
) -> ExecutionPlan:
    """Resolve a chat Research Job plan.

    Priority for ``model_override`` (when present and allowlisted):
    1. Explicit request model
    2. Conversation-stored model (thread continuity)

    If neither is allowlisted, the Capability Router picks the default model
    for ``chat`` + policy.
    """
    allow = set(allowlisted_models or ())
    override = None
    req = (requested_model or "").strip()
    if req and (not allow or req in allow):
        override = req
    else:
        conv = (conversation_model or "").strip()
        if conv and (not allow or conv in allow):
            override = conv

    policy = execution_policy
    if not policy:
        policy = execution_policy_from_mode(quality_mode)

    return resolve_execution(
        ResearchJob.CHAT,
        execution_policy=policy,
        model_override=override,
    )
