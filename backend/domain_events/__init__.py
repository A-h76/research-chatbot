"""Internal synchronous Domain Event Bus — business events only (Bite 14).

Not Kafka. Not Redis Pub/Sub. Not for UI events.
"""

from __future__ import annotations

from backend.domain_events.bus import DomainEventBus, get_bus, publish, set_bus, subscribe
from backend.domain_events.catalog import (
    AI_EXECUTION_COMPLETED,
    DOMAIN_EVENT_NAMES,
    EVIDENCE_ACCEPTED,
    PAPER_IMPORTED,
    RESEARCH_DECISION_RECORDED,
    WRITING_GENERATED,
)
from backend.domain_events.types import (
    DomainEvent,
    ai_execution_completed,
    evidence_accepted,
    make_domain_event,
    paper_imported,
    research_decision_recorded,
    writing_generated,
)

DOMAIN_EVENTS_VERSION = "1.0"

__all__ = [
    "DOMAIN_EVENTS_VERSION",
    "DOMAIN_EVENT_NAMES",
    "PAPER_IMPORTED",
    "EVIDENCE_ACCEPTED",
    "WRITING_GENERATED",
    "RESEARCH_DECISION_RECORDED",
    "AI_EXECUTION_COMPLETED",
    "DomainEvent",
    "DomainEventBus",
    "get_bus",
    "set_bus",
    "publish",
    "subscribe",
    "make_domain_event",
    "paper_imported",
    "evidence_accepted",
    "writing_generated",
    "research_decision_recorded",
    "ai_execution_completed",
]
