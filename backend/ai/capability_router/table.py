"""Tier A routing table — capability + policy → provider + model.

Model strings are internal and replaceable. Product language stays on
Research Job / Capability / Execution Policy (ADR-0016).

Tier A: OpenAI, Anthropic, Google only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from backend.ai.capability_router.types import (
    Capability,
    ExecutionPolicy,
    Provider,
    ResearchJob,
)


@dataclass(frozen=True)
class RouteTarget:
    provider: Provider
    model: str
    notes: str = ""


# Job → primary capability (Level 1 → 2)
JOB_CAPABILITY: dict[ResearchJob, Capability] = {
    ResearchJob.CHAT: Capability.SCIENTIFIC_REASONING,
    ResearchJob.ANALYZE_PAPER: Capability.SCIENTIFIC_REASONING,
    ResearchJob.COMPARE_PAPERS: Capability.SCIENTIFIC_REASONING,
    ResearchJob.LITERATURE_REVIEW: Capability.DEEP_SYNTHESIS,
    ResearchJob.REVIEWER: Capability.ACADEMIC_WRITING,
    ResearchJob.WRITING: Capability.ACADEMIC_WRITING,
    ResearchJob.SEARCH: Capability.TOOL_USE,
    ResearchJob.OCR: Capability.VISION,
    ResearchJob.EVIDENCE_EXTRACTION: Capability.STRUCTURED_EXTRACTION,
    ResearchJob.BULK_PROCESSING: Capability.BULK_PROCESSING,
}

# Default policy when caller omits one
JOB_DEFAULT_POLICY: dict[ResearchJob, ExecutionPolicy] = {
    ResearchJob.CHAT: ExecutionPolicy.BALANCED,
    ResearchJob.ANALYZE_PAPER: ExecutionPolicy.BALANCED,
    ResearchJob.COMPARE_PAPERS: ExecutionPolicy.HIGHEST_QUALITY,
    ResearchJob.LITERATURE_REVIEW: ExecutionPolicy.HIGHEST_QUALITY,
    ResearchJob.REVIEWER: ExecutionPolicy.BALANCED,
    ResearchJob.WRITING: ExecutionPolicy.BALANCED,
    ResearchJob.SEARCH: ExecutionPolicy.BALANCED,
    ResearchJob.OCR: ExecutionPolicy.BALANCED,
    ResearchJob.EVIDENCE_EXTRACTION: ExecutionPolicy.LOWEST_COST,
    ResearchJob.BULK_PROCESSING: ExecutionPolicy.LOWEST_COST,
}

# Env overrides keep ops flexible without renaming capabilities
def _m(env_key: str, default: str) -> str:
    return (os.environ.get(env_key) or default).strip()


# Capability × policy → Tier A target
# Keys omitted fall back via resolve.py cascade.
ROUTE_TABLE: dict[tuple[Capability, ExecutionPolicy], RouteTarget] = {
    # Scientific reasoning
    (Capability.SCIENTIFIC_REASONING, ExecutionPolicy.HIGHEST_QUALITY): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_REASONING_HQ", "gpt-5.5-pro"),
        "hard methodology / design critique",
    ),
    (Capability.SCIENTIFIC_REASONING, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_REASONING_BALANCED", "gpt-5.5"),
        "default analysis / compare",
    ),
    (Capability.SCIENTIFIC_REASONING, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_REASONING_ECONOMY", "gpt-5-mini"),
        "economy reasoning",
    ),
    (Capability.SCIENTIFIC_REASONING, ExecutionPolicy.FASTEST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_REASONING_FAST", "gpt-5-mini"),
        "latency-first reasoning",
    ),
    # Deep synthesis
    (Capability.DEEP_SYNTHESIS, ExecutionPolicy.HIGHEST_QUALITY): RouteTarget(
        Provider.ANTHROPIC,
        _m("ACR_MODEL_SYNTHESIS_HQ", "claude-sonnet-4-20250514"),
        "literature synthesis quality-first",
    ),
    (Capability.DEEP_SYNTHESIS, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_SYNTHESIS_BALANCED", "gpt-5.5"),
        "multi-paper synthesis",
    ),
    (Capability.DEEP_SYNTHESIS, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_SYNTHESIS_ECONOMY", "gpt-5-mini"),
        "economy synthesis",
    ),
    # Academic writing + critique
    (Capability.ACADEMIC_WRITING, ExecutionPolicy.HIGHEST_QUALITY): RouteTarget(
        Provider.ANTHROPIC,
        _m("ACR_MODEL_WRITING_HQ", "claude-sonnet-4-20250514"),
        "publication-grade prose / critique",
    ),
    (Capability.ACADEMIC_WRITING, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.ANTHROPIC,
        _m("ACR_MODEL_WRITING_BALANCED", "claude-sonnet-4-20250514"),
        "default writing / reviewer",
    ),
    (Capability.ACADEMIC_WRITING, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_WRITING_ECONOMY", "gpt-5-mini"),
        "economy drafting",
    ),
    (Capability.ACADEMIC_WRITING, ExecutionPolicy.FASTEST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_WRITING_FAST", "gpt-5-mini"),
        "fast drafting",
    ),
    # Long context / vision — Google
    (Capability.LONG_CONTEXT, ExecutionPolicy.HIGHEST_QUALITY): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_LONGCTX_HQ", "gemini-2.5-pro"),
        "huge literature collections",
    ),
    (Capability.LONG_CONTEXT, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_LONGCTX_BALANCED", "gemini-2.5-pro"),
        "large context",
    ),
    (Capability.LONG_CONTEXT, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_LONGCTX_ECONOMY", "gemini-2.5-flash"),
        "economy long context",
    ),
    (Capability.VISION, ExecutionPolicy.HIGHEST_QUALITY): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_VISION_HQ", "gemini-2.5-pro"),
        "multimodal pages / figures",
    ),
    (Capability.VISION, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_VISION_BALANCED", "gemini-2.5-flash"),
        "OCR / page understanding",
    ),
    (Capability.VISION, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_VISION_ECONOMY", "gemini-2.5-flash"),
        "economy vision",
    ),
    (Capability.VISION, ExecutionPolicy.FASTEST): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_VISION_FAST", "gemini-2.5-flash"),
        "fast OCR",
    ),
    # Structured / tools / bulk — OpenAI + Flash economy
    (Capability.STRUCTURED_EXTRACTION, ExecutionPolicy.HIGHEST_QUALITY): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_EXTRACT_HQ", "gpt-5.5"),
        "high-quality structured extract",
    ),
    (Capability.STRUCTURED_EXTRACTION, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_EXTRACT_BALANCED", "gpt-5-mini"),
        "default extract",
    ),
    (Capability.STRUCTURED_EXTRACTION, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_EXTRACT_ECONOMY", "gpt-5-mini"),
        "bulk extract economy",
    ),
    (Capability.TOOL_USE, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_TOOLS_BALANCED", "gpt-5.5"),
        "search / tool orchestration",
    ),
    (Capability.TOOL_USE, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_TOOLS_ECONOMY", "gpt-5-mini"),
        "economy tools",
    ),
    (Capability.BULK_PROCESSING, ExecutionPolicy.LOWEST_COST): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_BULK_ECONOMY", "gemini-2.5-flash"),
        "large-N triage",
    ),
    (Capability.BULK_PROCESSING, ExecutionPolicy.FASTEST): RouteTarget(
        Provider.GOOGLE,
        _m("ACR_MODEL_BULK_FAST", "gemini-2.5-flash"),
        "fast bulk",
    ),
    (Capability.BULK_PROCESSING, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_BULK_BALANCED", "gpt-5-mini"),
        "bulk balanced",
    ),
    (Capability.CODE, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_CODE_BALANCED", "gpt-5.5"),
        "research + code",
    ),
    (Capability.TRANSLATION, ExecutionPolicy.BALANCED): RouteTarget(
        Provider.OPENAI,
        _m("ACR_MODEL_TRANSLATION_BALANCED", "gpt-5-mini"),
        "translation",
    ),
}

# Policy cascade when exact (capability, policy) missing
_POLICY_FALLBACK: list[ExecutionPolicy] = [
    ExecutionPolicy.BALANCED,
    ExecutionPolicy.HIGHEST_QUALITY,
    ExecutionPolicy.LOWEST_COST,
    ExecutionPolicy.FASTEST,
]
