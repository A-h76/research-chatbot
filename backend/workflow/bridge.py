"""Bridge Domain Event Bus → Research Workflow Engine (Bite 15).

Handlers are idempotent via the domain event bus delivery dedupe.
"""

from __future__ import annotations

import logging

from backend.domain_events import (
    EVIDENCE_ACCEPTED,
    PAPER_IMPORTED,
    RESEARCH_DECISION_RECORDED,
    WRITING_GENERATED,
    DomainEvent,
    subscribe,
)
from backend.workflow.definitions import STEP_EVIDENCE
from backend.workflow.engine import get_engine

logger = logging.getLogger("backend.workflow.bridge")

_BRIDGES_REGISTERED = False


def register_workflow_bridges() -> None:
    """Idempotent process-wide subscription (safe to call from composition root)."""
    global _BRIDGES_REGISTERED
    if _BRIDGES_REGISTERED:
        return
    subscribe(_on_paper_imported, event_name=PAPER_IMPORTED, handler_key="wf.paper_imported")
    subscribe(_on_writing_generated, event_name=WRITING_GENERATED, handler_key="wf.writing")
    subscribe(_on_evidence_accepted, event_name=EVIDENCE_ACCEPTED, handler_key="wf.evidence")
    subscribe(
        _on_research_decision,
        event_name=RESEARCH_DECISION_RECORDED,
        handler_key="wf.decision",
    )
    _BRIDGES_REGISTERED = True
    logger.info("workflow domain-event bridges registered")


def _on_paper_imported(event: DomainEvent) -> None:
    p = event.payload
    source = str(p.get("source") or "")
    held = source in ("held_bytes", "google_drive", "onedrive", "dropbox", "manual") or (
        "drive" in source.lower()
    )
    get_engine().note_paper_imported(
        user_id=int(p["user_id"]),
        file_id=int(p["file_id"]),
        project_id=p.get("project_id"),
        source=source,
        has_held_pdf=held,
    )


def _on_writing_generated(event: DomainEvent) -> None:
    p = event.payload
    get_engine().note_writing_generated(
        user_id=int(p["user_id"]),
        project_id=p.get("project_id"),
        execution_id=p.get("execution_id"),
    )


def _on_evidence_accepted(event: DomainEvent) -> None:
    p = event.payload
    if p.get("project_id") is None:
        return
    get_engine().complete_step_for_project(
        user_id=int(p["user_id"]),
        project_id=int(p["project_id"]),
        step=STEP_EVIDENCE,
        meta={"evidence_id": p.get("evidence_id"), "review_status": p.get("review_status")},
    )


def _on_research_decision(event: DomainEvent) -> None:
    p = event.payload
    get_engine().note_review_recorded(
        user_id=int(p["user_id"]),
        project_id=p.get("project_id"),
        evidence_id=p.get("evidence_id"),
        decision_type=str(p.get("decision_type") or ""),
    )
