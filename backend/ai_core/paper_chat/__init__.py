"""Stage 1 Paper Chat pipeline helpers — flag, plan, shadow hash parity."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Literal

from backend.ai_core.orchestration.prompt_router import PromptPlan, PromptRouter
from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt
from backend.ai_core.schemas.research_context import ResearchIntent
from backend.ai_core.versions import (
    CONTEXT_SCHEMA_VERSION,
    IDENTITY_VERSION,
    LEGACY_PAPER_CHAT_PROMPT_VERSION,
)

logger = logging.getLogger(__name__)

PaperChatPipelineMode = Literal["false", "true", "shadow"]

TEMPLATE_KEY = "legacy_paper_chat"


def paper_chat_pipeline_mode() -> PaperChatPipelineMode:
    """``PAPER_CHAT_PIPELINE_ENABLED``: false (default) | true | shadow."""
    raw = os.environ.get("PAPER_CHAT_PIPELINE_ENABLED", "false").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return "true"
    if raw == "shadow":
        return "shadow"
    return "false"


def prompt_text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def log_shadow_prompt_parity(*, legacy_prompt: str, pipeline_prompt: str) -> bool:
    """Log hash parity only — never full prompt bodies."""
    legacy_h = prompt_text_hash(legacy_prompt)
    pipeline_h = prompt_text_hash(pipeline_prompt)
    identical = legacy_h == pipeline_h
    logger.info(
        "paper_chat_stage1_shadow legacy_prompt_hash=%s pipeline_prompt_hash=%s "
        "identical=%s prompt_version=%s",
        legacy_h,
        pipeline_h,
        identical,
        LEGACY_PAPER_CHAT_PROMPT_VERSION,
    )
    return identical


def build_legacy_paper_chat_plan(
    *,
    user_name: str,
    paper_title: str,
    authors: str | None = None,
    year: int | str | None = None,
    venue: str | None = None,
    file_id: int | None = None,
    project_id: int | None = None,
    question: str | None = None,
    now: datetime | None = None,
    router: PromptRouter | None = None,
) -> PromptPlan:
    """Forced Stage 1 plan — no IdentityPack, no intent-inferred template."""
    if router is not None:
        return router.route_legacy_paper_chat(
            user_name=user_name,
            paper_title=paper_title,
            authors=authors,
            year=year,
            venue=venue,
            file_id=file_id,
            project_id=project_id,
            question=question,
            now=now,
        )
    system = render_legacy_paper_chat_prompt(
        user_name=user_name,
        paper_title=paper_title,
        authors=authors,
        year=year,
        venue=venue,
        now=now,
    )
    return PromptPlan(
        intent=ResearchIntent.READING,
        template_key=TEMPLATE_KEY,
        system_text=system,
        skill_text="",
        context_text="",
        question=question,
        identity_version=IDENTITY_VERSION,
        prompt_version=LEGACY_PAPER_CHAT_PROMPT_VERSION,
        context_schema_version=CONTEXT_SCHEMA_VERSION,
        metadata={
            "file_id": file_id,
            "project_id": project_id,
            "prompt_version": LEGACY_PAPER_CHAT_PROMPT_VERSION,
            "stage": "paper_chat_stage1",
            "identity_injected": False,
        },
    )


def resolve_paper_chat_system_prompt(
    *,
    user_name: str,
    paper_title: str,
    authors: str | None = None,
    year: int | str | None = None,
    venue: str | None = None,
    file_id: int | None = None,
    project_id: int | None = None,
    question: str | None = None,
    now: datetime | None = None,
    legacy_prompt: str | None = None,
) -> tuple[str, PromptPlan | None, PaperChatPipelineMode]:
    """Return (instructions, plan_or_none, mode) for the Paper Chat branch.

    - false: legacy text only (plan None)
    - shadow: legacy text served; plan built for hash logs
    - true: plan.system_text served
    """
    mode = paper_chat_pipeline_mode()
    legacy = legacy_prompt or render_legacy_paper_chat_prompt(
        user_name=user_name,
        paper_title=paper_title,
        authors=authors,
        year=year,
        venue=venue,
        now=now,
    )
    if mode == "false":
        return legacy, None, mode

    plan = build_legacy_paper_chat_plan(
        user_name=user_name,
        paper_title=paper_title,
        authors=authors,
        year=year,
        venue=venue,
        file_id=file_id,
        project_id=project_id,
        question=question,
        now=now,
    )
    if mode == "shadow":
        log_shadow_prompt_parity(legacy_prompt=legacy, pipeline_prompt=plan.system_text)
        return legacy, plan, mode
    return plan.system_text, plan, mode


def log_stage1_execution(result: Any) -> None:
    """Structured observability for a completed Stage 1 paper chat turn."""
    meta = getattr(result, "metadata", None) or {}
    validator = getattr(result, "validator", None)
    logger.info(
        "paper_chat_stage1_exec model=%s prompt_version=%s identity_version=%s "
        "context_schema_version=%s latency_ms=%s tokens=%s validator_ok=%s "
        "validator_warnings=%s file_id=%s plan_hash=%s",
        getattr(result, "model", ""),
        getattr(result, "prompt_version", ""),
        getattr(result, "identity_version", ""),
        getattr(result, "context_schema_version", ""),
        getattr(result, "latency_ms", 0),
        getattr(getattr(result, "usage", None), "total_tokens", 0),
        getattr(validator, "ok", None),
        getattr(validator, "warnings", None),
        meta.get("file_id"),
        meta.get("plan_hash"),
    )
