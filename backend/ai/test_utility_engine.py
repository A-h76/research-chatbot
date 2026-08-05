"""Tests for utility_engine (Bite 8)."""

from __future__ import annotations

from backend.ai.capability_router.utility_resolve import (
    PROMPT_VERSION_COMPARE,
    resolve_compare_execution,
)
from backend.ai.utility_engine import invoke_embed_texts, invoke_prompt_llm, invoke_query_embedding


class _StubGateway:
    def __init__(self):
        self.calls = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "content": '{"ok": true}',
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
            "cost": 0.002,
        }


class _StubRegistry:
    pass


def test_invoke_prompt_llm_records_ledger(monkeypatch):
    recorded = []

    def _record(entry, **kwargs):
        recorded.append(entry)

    monkeypatch.setattr("backend.ai.ledger_facade.record_acr_execution", _record)

    gw = _StubGateway()
    plan = resolve_compare_execution()
    content, prov = invoke_prompt_llm(
        ai_gateway=gw,
        model_registry=_StubRegistry(),
        prompt="compare these",
        plan=plan,
        prompt_version=PROMPT_VERSION_COMPARE,
        path="compare_papers",
        task="compare",
        user_id=42,
        json_mode=True,
    )
    assert content == '{"ok": true}'
    assert prov is not None
    assert gw.calls
    assert gw.calls[0]["response_format"] == {"type": "json_object"}
    assert recorded
    assert recorded[0].research_job == "compare_papers"


def test_invoke_embed_texts_returns_vectors(monkeypatch):
    recorded = []

    def _record(entry, **kwargs):
        recorded.append(entry)

    monkeypatch.setattr("backend.ai.ledger_facade.record_acr_execution", _record)

    class _Reg:
        embed_model = "text-embedding-3-small"

        def embed(self, text, user_id=None, skip_cost_ledger=False):
            self._last_embed_tokens = 3
            return [0.1, 0.2, 0.3]

    out = invoke_embed_texts(model_registry=_Reg(), texts=["hello"], user_id=7)
    assert out == [[0.1, 0.2, 0.3]]
    assert recorded
    assert recorded[0].research_job == "search"


def test_invoke_query_embedding_raises_on_failure():
    from backend.ai import ModelError

    class _Reg:
        embed_model = "text-embedding-3-small"

        def embed(self, text, user_id=None):
            raise RuntimeError("api down")

    try:
        invoke_query_embedding(
            model_registry=_Reg(),
            text="query",
            user_id=1,
            path="api_documents_search",
        )
        assert False, "expected ModelError"
    except ModelError:
        pass
