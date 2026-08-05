"""Domain event value types and constructors."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.domain_events.catalog import (
    AI_EXECUTION_COMPLETED,
    EVIDENCE_ACCEPTED,
    PAPER_IMPORTED,
    RESEARCH_DECISION_RECORDED,
    WRITING_GENERATED,
    assert_domain_event_name,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DomainEvent:
    """Immutable business fact published on the in-process bus.

    ``event_id`` is the idempotency key: republishing the same id to the same
    handler is a no-op. Prefer deterministic ids tied to the aggregate when
    the same business action may be retried.
    """

    name: str
    event_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=_utcnow_iso)
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        assert_domain_event_name(self.name)
        if not self.event_id:
            raise ValueError("event_id is required for idempotent handlers")


def new_event_id() -> str:
    return str(uuid.uuid4())


def make_domain_event(
    name: str,
    *,
    event_id: str | None = None,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    occurred_at: str | None = None,
) -> DomainEvent:
    return DomainEvent(
        name=assert_domain_event_name(name),
        event_id=event_id or new_event_id(),
        payload=dict(payload or {}),
        occurred_at=occurred_at or _utcnow_iso(),
        correlation_id=correlation_id,
    )


def paper_imported(
    *,
    user_id: int,
    file_id: int,
    project_id: int | None = None,
    source: str = "",
    already_exists: bool = False,
    correlation_id: str | None = None,
) -> DomainEvent:
    """Emitted when a library paper row is newly acquired (not a dedupe hit)."""
    return make_domain_event(
        PAPER_IMPORTED,
        event_id=f"paper-imported:{int(file_id)}",
        payload={
            "user_id": int(user_id),
            "file_id": int(file_id),
            "project_id": int(project_id) if project_id is not None else None,
            "source": (source or "")[:80],
            "already_exists": bool(already_exists),
        },
        correlation_id=correlation_id,
    )


def evidence_accepted(
    *,
    user_id: int,
    evidence_id: int,
    project_id: int | None = None,
    review_status: str = "accepted",
    correlation_id: str | None = None,
) -> DomainEvent:
    return make_domain_event(
        EVIDENCE_ACCEPTED,
        event_id=f"evidence-accepted:{int(evidence_id)}:{review_status}",
        payload={
            "user_id": int(user_id),
            "evidence_id": int(evidence_id),
            "project_id": int(project_id) if project_id is not None else None,
            "review_status": review_status,
        },
        correlation_id=correlation_id,
    )


def writing_generated(
    *,
    user_id: int,
    project_id: int | None = None,
    execution_id: str | None = None,
    document_id: int | None = None,
    evidence_source_ids: list[int] | None = None,
    correlation_id: str | None = None,
) -> DomainEvent:
    eid = execution_id or new_event_id()
    return make_domain_event(
        WRITING_GENERATED,
        event_id=f"writing-generated:{eid}",
        payload={
            "user_id": int(user_id),
            "project_id": int(project_id) if project_id is not None else None,
            "execution_id": eid,
            "document_id": int(document_id) if document_id is not None else None,
            "evidence_source_ids": list(evidence_source_ids or []),
        },
        correlation_id=correlation_id,
    )


def research_decision_recorded(
    *,
    user_id: int,
    decision_id: int,
    project_id: int | None = None,
    evidence_id: int | None = None,
    decision_type: str = "",
    correlation_id: str | None = None,
) -> DomainEvent:
    return make_domain_event(
        RESEARCH_DECISION_RECORDED,
        event_id=f"research-decision:{int(decision_id)}",
        payload={
            "user_id": int(user_id),
            "decision_id": int(decision_id),
            "project_id": int(project_id) if project_id is not None else None,
            "evidence_id": int(evidence_id) if evidence_id is not None else None,
            "decision_type": (decision_type or "")[:80],
        },
        correlation_id=correlation_id,
    )


def ai_execution_completed(
    *,
    execution_id: str,
    user_id: int | None = None,
    model: str = "",
    status: str = "completed",
    task: str = "",
    correlation_id: str | None = None,
) -> DomainEvent:
    return make_domain_event(
        AI_EXECUTION_COMPLETED,
        event_id=f"ai-execution:{execution_id}",
        payload={
            "execution_id": str(execution_id),
            "user_id": int(user_id) if user_id is not None else None,
            "model": (model or "")[:120],
            "status": (status or "completed")[:40],
            "task": (task or "")[:80],
        },
        correlation_id=correlation_id,
    )
