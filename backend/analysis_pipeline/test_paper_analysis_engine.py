"""Bite 6 — SUE paper analysis ACR + ledger."""

from __future__ import annotations

from backend.ai.ai_ledger import clear_ledger_for_tests, recent_executions
from backend.analysis_pipeline.paper_analysis_engine import (
    invoke_paper_analysis_llm,
    record_phase1_pipeline_execution,
)


class _FakeGateway:
    def __init__(self):
        self.calls: list[dict] = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "content": '{"executive_summary":"ok"}',
            "total_tokens": 40,
            "prompt_tokens": 30,
            "completion_tokens": 10,
            "cost": 0.01,
            "model": kwargs.get("model", "gpt-test"),
        }


class _FakeRegistry:
    pass


def test_invoke_paper_analysis_llm_records_ledger():
    clear_ledger_for_tests()
    gateway = _FakeGateway()
    result, provenance = invoke_paper_analysis_llm(
        ai_gateway=gateway,
        model_registry=_FakeRegistry(),
        messages=[{"role": "user", "content": "analyze"}],
        user_id=5,
        file_id=9,
        project_id=2,
        quality_mode="balanced",
    )
    assert result["content"]
    assert provenance
    assert gateway.calls
    assert gateway.calls[0]["model"]
    ledger = recent_executions(limit=1)[0]
    assert ledger["research_job"] == "analyze_paper"
    assert ledger["trace_id"]
    assert ledger["extra"]["path"] == "paper_analysis"


def test_record_phase1_pipeline_execution_is_deterministic():
    clear_ledger_for_tests()
    provenance = record_phase1_pipeline_execution(
        file_id=9,
        user_id=5,
        project_id=2,
        content_hash="abc123",
        status="completed",
        phase_keys=["document_understanding", "knowledge_graph"],
        latency_ms=120,
    )
    assert provenance
    ledger = recent_executions(limit=1)[0]
    assert ledger["research_job"] == "analyze_paper"
    assert ledger["evaluation"]["validation_kind"] == "deterministic"
    assert ledger["extra"]["no_llm_invocation"] is True
    assert ledger["extra"]["path"] == "phase1_analysis"
