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
from backend.ai.capability_router.writing_resolve import (
    PROMPT_VERSION_WRITING_ASSISTANT,
    resolve_writing_assistant_execution,
)
from backend.ai.capability_router.reviewer_resolve import (
    PROMPT_VERSION_REVIEWER,
    resolve_reviewer_execution,
)
from backend.ai.capability_router.evidence_extract_resolve import (
    PROMPT_VERSION_EVIDENCE_EXTRACT,
    resolve_evidence_extract_execution,
)
from backend.ai.capability_router.paper_analysis_resolve import (
    PROMPT_VERSION_PAPER_ANALYSIS,
    PROMPT_VERSION_PHASE1_PIPELINE,
    resolve_paper_analysis_execution,
    resolve_phase1_pipeline_execution,
)
from backend.ai.capability_router.search_resolve import (
    PROMPT_VERSION_RAG,
    resolve_search_execution,
)
from backend.ai.capability_router.utility_resolve import (
    PROMPT_VERSION_COMPARE,
    PROMPT_VERSION_EMBED,
    PROMPT_VERSION_GAPS,
    PROMPT_VERSION_MEMORY,
    PROMPT_VERSION_METADATA,
    PROMPT_VERSION_PROJECT_RESEARCH,
    PROMPT_VERSION_TITLE,
    resolve_compare_execution,
    resolve_embed_execution,
    resolve_gaps_execution,
    resolve_memory_extraction_execution,
    resolve_metadata_extraction_execution,
    resolve_project_research_execution,
    resolve_title_generation_execution,
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
    "resolve_writing_assistant_execution",
    "resolve_reviewer_execution",
    "resolve_evidence_extract_execution",
    "resolve_paper_analysis_execution",
    "resolve_phase1_pipeline_execution",
    "resolve_search_execution",
    "PROMPT_VERSION_CHAT",
    "PROMPT_VERSION_WRITING_ASSISTANT",
    "PROMPT_VERSION_REVIEWER",
    "PROMPT_VERSION_EVIDENCE_EXTRACT",
    "PROMPT_VERSION_PAPER_ANALYSIS",
    "PROMPT_VERSION_PHASE1_PIPELINE",
    "PROMPT_VERSION_RAG",
    "PROMPT_VERSION_COMPARE",
    "PROMPT_VERSION_GAPS",
    "PROMPT_VERSION_PROJECT_RESEARCH",
    "PROMPT_VERSION_METADATA",
    "PROMPT_VERSION_MEMORY",
    "PROMPT_VERSION_TITLE",
    "PROMPT_VERSION_EMBED",
    "resolve_compare_execution",
    "resolve_gaps_execution",
    "resolve_project_research_execution",
    "resolve_metadata_extraction_execution",
    "resolve_memory_extraction_execution",
    "resolve_title_generation_execution",
    "resolve_embed_execution",
    "legacy_gateway_task",
    "legacy_quality_mode",
    "execution_policy_from_mode",
]
