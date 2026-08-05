"""Bite 7 — Search RAG ACR + ledger."""

from __future__ import annotations

from backend.ai.ai_ledger import clear_ledger_for_tests, recent_executions
from backend.search.search_engine import invoke_rag_llm


class _FakeGateway:
    def __init__(self):
        self.calls: list[dict] = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "content": "Answer from RAG.",
            "total_tokens": 25,
            "prompt_tokens": 18,
            "completion_tokens": 7,
            "cost": 0.005,
            "model": kwargs.get("model", "gpt-test"),
        }


class _FakeRegistry:
    pass


def test_invoke_rag_llm_records_ledger():
    clear_ledger_for_tests()
    gateway = _FakeGateway()
    result, provenance = invoke_rag_llm(
        ai_gateway=gateway,
        model_registry=_FakeRegistry(),
        messages=[{"role": "user", "content": "What is X?"}],
        user_id=3,
        project_id=9,
        source_chunk_ids=[101, 102],
        quality_mode="balanced",
    )
    assert result["content"]
    assert provenance
    assert gateway.calls[0]["model"]
    ledger = recent_executions(limit=1)[0]
    assert ledger["research_job"] == "search"
    assert ledger["trace_id"]
    assert ledger["extra"]["path"] == "api_rag"
    assert ledger["evidence_source_ids"] == ["101", "102"]
