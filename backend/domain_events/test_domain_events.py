"""Bite 14 — internal synchronous Domain Event Bus."""

from __future__ import annotations

import pytest

from backend.domain_events import (
    DOMAIN_EVENT_NAMES,
    DOMAIN_EVENTS_VERSION,
    DomainEventBus,
    AI_EXECUTION_COMPLETED,
    EVIDENCE_ACCEPTED,
    PAPER_IMPORTED,
    RESEARCH_DECISION_RECORDED,
    WRITING_GENERATED,
    ai_execution_completed,
    evidence_accepted,
    get_bus,
    make_domain_event,
    paper_imported,
    publish,
    research_decision_recorded,
    set_bus,
    subscribe,
    writing_generated,
)


@pytest.fixture(autouse=True)
def _isolated_bus():
    bus = DomainEventBus()
    set_bus(bus)
    yield bus
    bus.clear()
    set_bus(None)


def test_catalog_lists_business_events_only():
    assert DOMAIN_EVENTS_VERSION == "1.0"
    assert PAPER_IMPORTED in DOMAIN_EVENT_NAMES
    assert EVIDENCE_ACCEPTED in DOMAIN_EVENT_NAMES
    assert WRITING_GENERATED in DOMAIN_EVENT_NAMES
    assert RESEARCH_DECISION_RECORDED in DOMAIN_EVENT_NAMES
    assert AI_EXECUTION_COMPLETED in DOMAIN_EVENT_NAMES
    assert "analysis_view_opened" not in DOMAIN_EVENT_NAMES


def test_reject_ui_events():
    with pytest.raises(ValueError, match="non-domain|UI"):
        make_domain_event("ui.click", event_id="x")
    with pytest.raises(ValueError, match="non-domain|UI"):
        make_domain_event("analysis_view_opened", event_id="x")
    with pytest.raises(ValueError, match="unknown"):
        make_domain_event("SomeFutureEvent", event_id="x")


def test_publish_delivers_synchronously():
    seen = []

    def on_paper(evt):
        seen.append(evt.name)

    subscribe(on_paper, event_name=PAPER_IMPORTED, handler_key="test.on_paper")
    n = publish(paper_imported(user_id=1, file_id=42, project_id=9, source="pubmed"))
    assert n == 1
    assert seen == [PAPER_IMPORTED]


def test_handlers_are_idempotent_by_event_id():
    calls = []

    def on_ev(evt):
        calls.append(evt.event_id)

    subscribe(on_ev, event_name=EVIDENCE_ACCEPTED, handler_key="test.idem")
    evt = evidence_accepted(user_id=1, evidence_id=7, project_id=2)
    publish(evt)
    publish(evt)
    assert calls == [evt.event_id]


def test_handler_failure_does_not_abort_siblings():
    order = []

    def bad(_evt):
        order.append("bad")
        raise RuntimeError("boom")

    def good(_evt):
        order.append("good")

    subscribe(bad, event_name=WRITING_GENERATED, handler_key="test.bad")
    subscribe(good, event_name=WRITING_GENERATED, handler_key="test.good")
    publish(writing_generated(user_id=1, project_id=2, execution_id="exec-1"))
    assert order == ["bad", "good"]


def test_constructors_use_deterministic_ids():
    assert paper_imported(user_id=1, file_id=5).event_id == "paper-imported:5"
    assert research_decision_recorded(user_id=1, decision_id=9).event_id == "research-decision:9"
    assert ai_execution_completed(execution_id="abc").event_id == "ai-execution:abc"


def test_get_bus_singleton_after_set():
    assert get_bus() is not None
    publish(paper_imported(user_id=1, file_id=1))
