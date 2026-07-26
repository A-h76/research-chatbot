"""Route an intent (+ context + identity) to a prompt plan.

Does **not** call OpenAI. Does **not** touch Flask routes.
PromptBuilder / chat migration will consume ``PromptPlan`` later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from backend.ai_core.identity.loader import IdentityLoader, IdentityPack, load_identity
from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt
from backend.ai_core.schemas.research_context import ResearchContext, ResearchIntent
from backend.ai_core.versions import (
    CONTEXT_SCHEMA_VERSION,
    IDENTITY_VERSION,
    LEGACY_PAPER_CHAT_PROMPT_VERSION,
    prompt_version_for,
)

# intent → skill template key (future: ai_core/prompts/{key}.md or PromptRegistry)
_TEMPLATE_BY_INTENT: dict[ResearchIntent, str] = {
    ResearchIntent.QUESTION: "question",
    ResearchIntent.READING: "reading",
    ResearchIntent.COMPARE: "compare",
    ResearchIntent.WRITING: "writing",
    ResearchIntent.CRITIQUE: "critique",
    ResearchIntent.EXPLAIN: "explain",
    ResearchIntent.REVIEW: "review",
    ResearchIntent.GAP_ANALYSIS: "gap_analysis",
    ResearchIntent.CITATION: "citation",
    ResearchIntent.OUTLINE: "outline",
    ResearchIntent.UNKNOWN: "question",
}

_SKILL_BLURBS: dict[str, str] = {
    "question": "Answer the research question using only provided context.",
    "reading": "Summarise and explain what the documents support; evidence first.",
    "compare": "Compare papers along explicit criteria; surface agreements and conflicts.",
    "writing": "Draft grounded prose; every claim needs support or an explicit limitation.",
    "critique": "Critique methods and claims; separate reported findings from your judgment.",
    "explain": "Explain concepts as used in the provided papers; avoid textbook invention.",
    "review": "Produce a structured review of strengths, limits, and open questions.",
    "gap_analysis": "Identify gaps and asymmetries across the provided papers.",
    "citation": "Propose or format citations only from owned / provided bibliographic items.",
    "outline": "Propose an outline grounded in claims and evidence from context.",
}


@dataclass(frozen=True)
class PromptPlan:
    """Assembled prompt inputs for a single AI call (no model invocation).

    Immutable after ``PromptRouter.route``: executor and routes must not mutate
    fields or ``metadata``. Log ``to_json()`` / its hash as the executed plan.
    """

    intent: ResearchIntent
    template_key: str
    system_text: str
    skill_text: str
    context_text: str
    question: str | None = None
    identity_version: str = IDENTITY_VERSION
    prompt_version: str = ""
    context_schema_version: str = CONTEXT_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Nested mutability would defeat frozen=True; freeze metadata too.
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def messages(self) -> list[dict[str, str]]:
        """OpenAI-style message list (identity + skill as system; context + question as user)."""
        system = f"{self.system_text.strip()}\n\n# Task skill ({self.template_key})\n\n{self.skill_text.strip()}\n"
        user_parts = ["# Research context\n", self.context_text.strip(), "\n"]
        if self.question:
            user_parts.extend(["\n# User question\n", self.question.strip(), "\n"])
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "".join(user_parts)},
        ]

    def to_json(self) -> str:
        """Deterministic serialization for golden tests and execution stamps."""
        payload = {
            "intent": (
                self.intent.value if isinstance(self.intent, ResearchIntent) else self.intent
            ),
            "template_key": self.template_key,
            "system_text": self.system_text,
            "skill_text": self.skill_text,
            "context_text": self.context_text,
            "question": self.question,
            "identity_version": self.identity_version,
            "prompt_version": self.prompt_version,
            "context_schema_version": self.context_schema_version,
            "metadata": dict(self.metadata),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _coerce_intent(intent: ResearchIntent | str) -> ResearchIntent:
    if isinstance(intent, ResearchIntent):
        return intent
    return ResearchIntent(intent)


def _context_to_text(context: ResearchContext, *, max_chars: int = 12_000) -> str:
    """Serialize pure context for the model — truncate as a safety rail."""
    payload = {
        "intent": context.intent.value if isinstance(context.intent, ResearchIntent) else context.intent,
        "file_id": context.file_id,
        "project_id": context.project_id,
        "document": context.document,
        "classification": context.classification,
        "entities": context.entities,
        "evidence": context.evidence,
        "graph": context.graph,
        "narrative": context.narrative,
        "notes": context.notes,
        "citations": context.citations,
        "extras": context.extras,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n… [truncated]\n"
    return text


class PromptRouter:
    """Intent → identity + skill + context → ``PromptPlan``.

    Inject ``IdentityLoader`` (or a preloaded pack) — never open markdown here.
    """

    def __init__(
        self,
        *,
        identity_loader: IdentityLoader | None = None,
        identity_pack: IdentityPack | None = None,
    ) -> None:
        self._identity_loader = identity_loader
        self._identity_pack = identity_pack

    def route(
        self,
        intent: ResearchIntent | str,
        context: ResearchContext,
        *,
        question: str | None = None,
        **_: object,
    ) -> PromptPlan:
        resolved = _coerce_intent(intent)
        if context.intent != resolved:
            # Prefer explicit route intent; context.intent should usually match.
            pass
        pack = self._identity_pack or (
            self._identity_loader.load() if self._identity_loader else load_identity()
        )
        template_key = _TEMPLATE_BY_INTENT.get(resolved, "question")
        skill = _SKILL_BLURBS.get(template_key, _SKILL_BLURBS["question"])
        q = question if question is not None else context.question
        identity_ver = getattr(pack, "version", None) or IDENTITY_VERSION
        return PromptPlan(
            intent=resolved,
            template_key=template_key,
            system_text=pack.as_system_text(),
            skill_text=skill,
            context_text=_context_to_text(context),
            question=q,
            identity_version=identity_ver,
            prompt_version=prompt_version_for(template_key),
            context_schema_version=CONTEXT_SCHEMA_VERSION,
            metadata={
                "file_id": context.file_id,
                "project_id": context.project_id,
                "identity_version": identity_ver,
                "prompt_version": prompt_version_for(template_key),
                "context_schema_version": CONTEXT_SCHEMA_VERSION,
                "entity_count": len(context.entities),
                "evidence_count": len(context.evidence),
            },
        )

    def route_legacy_paper_chat(
        self,
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
    ) -> PromptPlan:
        """Stage 1 Paper Chat — forced legacy template, no IdentityPack."""
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
            template_key="legacy_paper_chat",
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
