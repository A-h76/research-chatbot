"""Default Execution Profiles per Research Job (requirements, not models)."""

from __future__ import annotations

from backend.ai.capability_router.types import (
    ContextNeed,
    ExecutionProfile,
    ReasoningDepth,
    ResearchJob,
    TemperatureBand,
)

JOB_DEFAULT_PROFILE: dict[ResearchJob, ExecutionProfile] = {
    ResearchJob.CHAT: ExecutionProfile(
        reasoning=ReasoningDepth.STANDARD,
        context=ContextNeed.MEDIUM,
        temperature=TemperatureBand.MEDIUM,
    ),
    ResearchJob.ANALYZE_PAPER: ExecutionProfile(
        reasoning=ReasoningDepth.DEEP,
        context=ContextNeed.MEDIUM,
        structured_output=True,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.COMPARE_PAPERS: ExecutionProfile(
        reasoning=ReasoningDepth.DEEP,
        context=ContextNeed.LARGE,
        structured_output=True,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.LITERATURE_REVIEW: ExecutionProfile(
        reasoning=ReasoningDepth.DEEP,
        context=ContextNeed.LARGE,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.REVIEWER: ExecutionProfile(
        reasoning=ReasoningDepth.DEEP,
        context=ContextNeed.MEDIUM,
        structured_output=True,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.WRITING: ExecutionProfile(
        reasoning=ReasoningDepth.STANDARD,
        context=ContextNeed.MEDIUM,
        temperature=TemperatureBand.MEDIUM,
    ),
    ResearchJob.SEARCH: ExecutionProfile(
        reasoning=ReasoningDepth.STANDARD,
        context=ContextNeed.MEDIUM,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.OCR: ExecutionProfile(
        reasoning=ReasoningDepth.LIGHT,
        context=ContextNeed.MEDIUM,
        vision=True,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.EVIDENCE_EXTRACTION: ExecutionProfile(
        reasoning=ReasoningDepth.STANDARD,
        context=ContextNeed.MEDIUM,
        structured_output=True,
        temperature=TemperatureBand.LOW,
    ),
    ResearchJob.BULK_PROCESSING: ExecutionProfile(
        reasoning=ReasoningDepth.LIGHT,
        context=ContextNeed.SMALL,
        structured_output=True,
        temperature=TemperatureBand.LOW,
    ),
}

# Prompt Registry name hints per job (versioned templates live in PromptRegistry)
JOB_PROMPT_NAME: dict[ResearchJob, str] = {
    ResearchJob.CHAT: "chat_system",
    ResearchJob.ANALYZE_PAPER: "paper_analysis",
    ResearchJob.COMPARE_PAPERS: "paper_compare",
    ResearchJob.LITERATURE_REVIEW: "literature_review",
    ResearchJob.REVIEWER: "reviewer",
    ResearchJob.WRITING: "section_generator",
    ResearchJob.SEARCH: "rag",
    ResearchJob.OCR: "ocr_vision",
    ResearchJob.EVIDENCE_EXTRACTION: "evidence_extract",
    ResearchJob.BULK_PROCESSING: "bulk_process",
}
