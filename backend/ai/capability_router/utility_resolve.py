"""Utility LLM + embed resolves (Evolution Bite 8)."""

from __future__ import annotations

from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    resolve_execution,
)
from backend.ai.capability_router.types import ExecutionPlan, ExecutionPolicy, ResearchJob

PROMPT_VERSION_COMPARE = "paper_compare@1.0"
PROMPT_VERSION_GAPS = "gap_finder@1.0"
PROMPT_VERSION_PROJECT_RESEARCH = "project_research@1.0"
PROMPT_VERSION_METADATA = "metadata_extract@1.0"
PROMPT_VERSION_MEMORY = "memory_extract@1.0"
PROMPT_VERSION_TITLE = "chat_title@1.0"
PROMPT_VERSION_EMBED = "embedding@1.0"


def resolve_compare_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    policy = execution_policy or execution_policy_from_mode(quality_mode or "balanced")
    return resolve_execution(ResearchJob.COMPARE_PAPERS, execution_policy=policy)


def resolve_gaps_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    policy = execution_policy or execution_policy_from_mode(quality_mode or "balanced")
    return resolve_execution(ResearchJob.LITERATURE_REVIEW, execution_policy=policy)


def resolve_project_research_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    policy = execution_policy or execution_policy_from_mode(quality_mode or "balanced")
    return resolve_execution(ResearchJob.LITERATURE_REVIEW, execution_policy=policy)


def resolve_metadata_extraction_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    policy = execution_policy or execution_policy_from_mode(quality_mode or "fast")
    return resolve_execution(ResearchJob.BULK_PROCESSING, execution_policy=policy)


def resolve_memory_extraction_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    policy = execution_policy or execution_policy_from_mode(quality_mode or "fast")
    return resolve_execution(ResearchJob.BULK_PROCESSING, execution_policy=policy)


def resolve_title_generation_execution(
    *,
    quality_mode: str | None = None,
    execution_policy: str | ExecutionPolicy | None = None,
) -> ExecutionPlan:
    policy = execution_policy or execution_policy_from_mode(quality_mode or "fast")
    return resolve_execution(ResearchJob.BULK_PROCESSING, execution_policy=policy)


def resolve_embed_execution() -> ExecutionPlan:
    return resolve_execution(ResearchJob.SEARCH, execution_policy=ExecutionPolicy.LOWEST_COST)
