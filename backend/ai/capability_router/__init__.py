"""AI Capability Router — Research OS execution backbone v1.0

Status: Frozen (ADR-0016)

===========================================================================
INTEGRATION BOUNDARY (binding)
---------------------------------------------------------------------------
Feature code declares a Research Job (+ optional Execution Policy / Profile).
It must NOT pick providers or model brands in product UX.

    from backend.ai.capability_router import resolve_execution
    from backend.ai.ai_ledger import record_execution, AILedgerEntry

    plan = resolve_execution("literature_review", execution_policy="highest_quality")
    # … gateway call …
    record_execution(AILedgerEntry.from_plan(plan, prompt_version=…, …))

Flow: Job → Profile → Policy → Router → Prompt Registry → Model Registry
      → Gateway → Evidence-Based Validation → AI Ledger → Artifact
===========================================================================

Contract: docs/contracts/ai-capability-router-contract.md
ADR:      docs/adr/0016-ai-capability-router.md
"""

from __future__ import annotations

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    legacy_gateway_task,
    legacy_quality_mode,
    resolve_execution,
)
from backend.ai.capability_router.chat_resolve import (
    PROMPT_VERSION_CHAT,
    resolve_chat_execution,
)
from backend.ai.capability_router.types import (
    ACR_STATUS,
    ACR_VERSION,
    AIExecutionProvenance,
    Capability,
    ContextNeed,
    ExecutionPlan,
    ExecutionPolicy,
    ExecutionProfile,
    Provider,
    ReasoningDepth,
    ResearchJob,
    TemperatureBand,
)

__all__ = [
    "ACR_VERSION",
    "ACR_STATUS",
    "ResearchJob",
    "Capability",
    "ExecutionProfile",
    "ExecutionPolicy",
    "Provider",
    "ExecutionPlan",
    "AIExecutionProvenance",
    "ReasoningDepth",
    "ContextNeed",
    "TemperatureBand",
    "resolve_execution",
    "resolve_chat_execution",
    "PROMPT_VERSION_CHAT",
    "legacy_gateway_task",
    "legacy_quality_mode",
    "execution_policy_from_mode",
]
