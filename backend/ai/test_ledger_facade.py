"""Tests for ledger_facade (Bite 11)."""

from __future__ import annotations

from backend.ai.ai_ledger import AILedgerEntry, clear_ledger_for_tests, recent_executions
from backend.ai.capability_router.utility_resolve import resolve_compare_execution
from backend.ai.ledger_facade import CostProjection, record_platform_execution, record_acr_execution


class _StubCostLedger:
    def __init__(self):
        self.logged = []

    def estimate_cost(self, model, prompt_tokens, completion_tokens):
        return 0.01

    def log(self, db_session, **kwargs):
        self.logged.append(kwargs)


class _StubRegistry:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._cost_ledger = _StubCostLedger()


def test_record_platform_execution_writes_ai_and_cost_ledgers():
    clear_ledger_for_tests()
    plan = resolve_compare_execution()
    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version="compare@v1",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.01,
    )
    registry = _StubRegistry(db_session=object())
    payload = record_acr_execution(
        entry,
        model_registry=registry,
        user_id=7,
        cost_action="analysis",
    )
    assert payload.get("execution_id")
    assert recent_executions(limit=1)
    assert len(registry._cost_ledger.logged) == 1
    row = registry._cost_ledger.logged[0]
    assert row["user_id"] == 7
    assert row["action"] == "analysis"
    assert row["prompt_tokens"] == 100
    assert row["completion_tokens"] == 50


def test_record_platform_execution_skips_cost_without_db():
    clear_ledger_for_tests()
    plan = resolve_compare_execution()
    entry = AILedgerEntry.from_plan(plan, prompt_version="compare@v1")
    registry = _StubRegistry(db_session=None)
    record_acr_execution(entry, model_registry=registry, user_id=7)
    assert recent_executions(limit=1)
    assert registry._cost_ledger.logged == []


def test_record_platform_execution_ai_gate():
    clear_ledger_for_tests()
    plan = resolve_compare_execution()
    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version="compare@v1",
        tokens_in=10,
        tokens_out=5,
    )

    class _Gate:
        def __init__(self):
            self.calls = []

        def record_usage(self, user_id, *, tokens, cost_usd, operation=None):
            self.calls.append(
                {"user_id": user_id, "tokens": tokens, "cost_usd": cost_usd, "operation": operation}
            )

    gate = _Gate()
    registry = _StubRegistry(db_session=object())
    record_platform_execution(
        entry,
        cost_projection=CostProjection(
            db_session=registry.db_session,
            cost_ledger=registry._cost_ledger,
            user_id=3,
            action="chat",
            ai_gate=gate,
            operation="chat",
        ),
    )
    assert gate.calls
    assert gate.calls[0]["user_id"] == 3
    assert gate.calls[0]["tokens"] == 15


def test_record_platform_execution_emits_ai_execution_completed():
    from backend.domain_events import (
        AI_EXECUTION_COMPLETED,
        DomainEventBus,
        set_bus,
        subscribe,
    )

    clear_ledger_for_tests()
    bus = DomainEventBus()
    set_bus(bus)
    seen = []
    subscribe(
        lambda e: seen.append(e),
        event_name=AI_EXECUTION_COMPLETED,
        handler_key="test.ledger.ai",
    )
    plan = resolve_compare_execution()
    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version="compare@v1",
        tokens_in=1,
        tokens_out=1,
        status="completed",
        extra={"user_id": 11},
    )
    payload = record_platform_execution(entry)
    assert payload.get("execution_id")
    assert len(seen) == 1
    assert seen[0].payload["execution_id"] == payload["execution_id"]
    assert seen[0].payload["user_id"] == 11
    # Idempotent republish
    record_platform_execution(entry)
    assert len(seen) == 1
    bus.clear()
    set_bus(None)
