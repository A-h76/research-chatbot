"""Dhund AI Core — the product brain.

Sprint 1–3: identity, context, router, validator.
Sprint 4: Phase 1 adapters + ``Phase1Retrieval``.
Sprint 4.5: ``AIExecutor`` + independent versioning (identity / prompt / context).
Sprint 5 Stage 1: Paper Chat pipeline behind ``PAPER_CHAT_PIPELINE_ENABLED``
(default OFF). See ``docs/ai-core-stage1-paper-chat.md``.
"""

from backend.ai_core.identity import IdentityLoader, IdentityPack, load_identity, load_identity_pack
from backend.ai_core.schemas.ai_response import AIResponse, ConfidenceLevel
from backend.ai_core.schemas.execution import AIExecutionResult, TokenUsage
from backend.ai_core.schemas.request import AIRequest
from backend.ai_core.schemas.research_context import ResearchContext, ResearchIntent
from backend.ai_core.schemas.workspace_reference import (
    WorkspaceReference,
    WorkspaceReferenceKind,
    WorkspaceTab,
)
from backend.ai_core.versions import (
    CONTEXT_SCHEMA_VERSION,
    IDENTITY_VERSION,
    LEGACY_PAPER_CHAT_PROMPT_VERSION,
)

__all__ = [
    "AIExecutionResult",
    "AIRequest",
    "AIResponse",
    "CONTEXT_SCHEMA_VERSION",
    "ConfidenceLevel",
    "IDENTITY_VERSION",
    "IdentityLoader",
    "IdentityPack",
    "LEGACY_PAPER_CHAT_PROMPT_VERSION",
    "ResearchContext",
    "ResearchIntent",
    "TokenUsage",
    "WorkspaceReference",
    "WorkspaceReferenceKind",
    "WorkspaceTab",
    "load_identity",
    "load_identity_pack",
]

__version__ = "0.5.0"  # Stage 1 Paper Chat pipeline (flagged)
