"""Allowed domain event names — business facts only.

Do not add UI / analytics / clickstream names here. Workflow instrumentation
(``backend.workflow.events``) and writing activity logs stay separate.
"""

from __future__ import annotations

# Canonical research-OS domain events (Bite 14).
PAPER_IMPORTED = "PaperImported"
EVIDENCE_ACCEPTED = "EvidenceAccepted"
WRITING_GENERATED = "WritingGenerated"
RESEARCH_DECISION_RECORDED = "ResearchDecisionRecorded"
AI_EXECUTION_COMPLETED = "AIExecutionCompleted"

DOMAIN_EVENT_NAMES: frozenset[str] = frozenset(
    {
        PAPER_IMPORTED,
        EVIDENCE_ACCEPTED,
        WRITING_GENERATED,
        RESEARCH_DECISION_RECORDED,
        AI_EXECUTION_COMPLETED,
    }
)

# Explicitly rejected — keep UI / product analytics off this bus.
_UI_OR_NON_DOMAIN_PREFIXES = (
    "ui.",
    "click.",
    "page.",
    "nav.",
    "toast.",
    "modal.",
)

_UI_OR_NON_DOMAIN_EXACT = frozenset(
    {
        "signup_started",
        "signup_completed",
        "onboarding_started",
        "onboarding_completed",
        "analysis_view_opened",
        "reviewer_opened",
    }
)


def is_ui_or_non_domain(name: str) -> bool:
    n = (name or "").strip()
    if not n:
        return True
    lower = n.lower()
    if lower in _UI_OR_NON_DOMAIN_EXACT:
        return True
    return any(lower.startswith(p) for p in _UI_OR_NON_DOMAIN_PREFIXES)


def assert_domain_event_name(name: str) -> str:
    n = (name or "").strip()
    if is_ui_or_non_domain(n):
        raise ValueError(f"refusing non-domain / UI event on DomainEventBus: {name!r}")
    if n not in DOMAIN_EVENT_NAMES:
        raise ValueError(
            f"unknown domain event {name!r}; register in DOMAIN_EVENT_NAMES before publishing"
        )
    return n
