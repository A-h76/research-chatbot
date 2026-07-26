"""Independent version stamps for observability and regression answers.

Bump these deliberately when doctrine / skill prompts / context shape change.
Every ``AIExecutionResult`` should record all three.
"""

from __future__ import annotations

# Doctrine markdown stack (IdentityLoader / IdentityPack).
IDENTITY_VERSION = "1.0.0"

# ResearchContext / RetrievedBundle field contract (adapters + builder).
CONTEXT_SCHEMA_VERSION = "2.0.0"

# Paper Chat Stage 1 — behaviour-identical legacy template (first-class; no string drift).
# PromptRouter, AIExecutionResult, and golden tests must import this symbol.
LEGACY_PAPER_CHAT_PROMPT_VERSION = "legacy_paper_chat_v1"

# Per-skill prompt blurb / template versions (PromptRouter).
PROMPT_VERSIONS: dict[str, str] = {
    "question": "question_v1",
    "reading": "reading_v1",
    "compare": "compare_v1",
    "writing": "writing_v1",
    "critique": "critique_v1",
    "explain": "explain_v1",
    "review": "review_v1",
    "gap_analysis": "gap_analysis_v1",
    "citation": "citation_v1",
    "outline": "outline_v1",
    "legacy_paper_chat": LEGACY_PAPER_CHAT_PROMPT_VERSION,
}


def prompt_version_for(template_key: str) -> str:
    return PROMPT_VERSIONS.get(template_key, f"{template_key}_v1")
