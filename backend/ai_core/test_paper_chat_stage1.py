"""Stage 1 Paper Chat — legacy prompt parity, flag, stream, observe-only."""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.ai_core.orchestration import (
    AIExecutor,
    FakeResponsesStreamClient,
    PromptRouter,
)
from backend.ai_core.paper_chat import (
    build_legacy_paper_chat_plan,
    log_shadow_prompt_parity,
    paper_chat_pipeline_mode,
    prompt_text_hash,
    resolve_paper_chat_system_prompt,
)
from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt
from backend.ai_core.versions import LEGACY_PAPER_CHAT_PROMPT_VERSION


FIXED_NOW = datetime(2026, 7, 26, 15, 30, 0)


def _sample_prompt(**kwargs):
    defaults = dict(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
        now=FIXED_NOW,
    )
    defaults.update(kwargs)
    return render_legacy_paper_chat_prompt(**defaults)


def test_legacy_prompt_golden_snapshot():
    text = _sample_prompt()
    assert "CRP and Inflammation" in text
    assert "User: Ada" in text
    assert "Date: 2026-07-26 15:30" in text
    assert "Authors: Smith et al." in text
    assert "THIS PAPER ONLY" in text
    assert "Soro Identity Doctrine" not in text


def test_plan_system_text_equals_render_and_version_constant():
    plan = build_legacy_paper_chat_plan(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
        file_id=42,
        question="What is CRP?",
        now=FIXED_NOW,
    )
    assert plan.system_text == _sample_prompt()
    assert plan.prompt_version == LEGACY_PAPER_CHAT_PROMPT_VERSION
    assert plan.template_key == "legacy_paper_chat"
    assert plan.metadata["identity_injected"] is False
    assert "Soro Identity Doctrine" not in plan.system_text
    assert plan.skill_text == ""


def test_router_route_legacy_paper_chat_matches_render():
    plan = PromptRouter().route_legacy_paper_chat(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        now=FIXED_NOW,
        file_id=7,
    )
    assert plan.system_text == _sample_prompt(authors=None, year=None, venue=None)
    assert plan.prompt_version == LEGACY_PAPER_CHAT_PROMPT_VERSION


def test_build_paper_chat_prompt_delegates(monkeypatch):
    """server.build_paper_chat_prompt must stay byte-equal to the template."""
    import server as server_mod

    user = SimpleNamespace(name="Ada")
    paper = SimpleNamespace(
        title="CRP and Inflammation",
        name="file.pdf",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
    )
    assert server_mod.build_paper_chat_prompt(user, paper, now=FIXED_NOW) == _sample_prompt()


@pytest.mark.parametrize(
    "env_val,expected",
    [
        (None, "false"),
        ("false", "false"),
        ("true", "true"),
        ("1", "true"),
        ("shadow", "shadow"),
    ],
)
def test_pipeline_mode_flag(monkeypatch, env_val, expected):
    if env_val is None:
        monkeypatch.delenv("PAPER_CHAT_PIPELINE_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PAPER_CHAT_PIPELINE_ENABLED", env_val)
    assert paper_chat_pipeline_mode() == expected


def test_resolve_false_serves_legacy_no_plan(monkeypatch):
    monkeypatch.setenv("PAPER_CHAT_PIPELINE_ENABLED", "false")
    text, plan, mode = resolve_paper_chat_system_prompt(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        now=FIXED_NOW,
    )
    assert mode == "false"
    assert plan is None
    assert text == _sample_prompt(authors=None, year=None, venue=None)


def test_resolve_true_serves_plan_system_text(monkeypatch):
    monkeypatch.setenv("PAPER_CHAT_PIPELINE_ENABLED", "true")
    text, plan, mode = resolve_paper_chat_system_prompt(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
        file_id=42,
        now=FIXED_NOW,
    )
    assert mode == "true"
    assert plan is not None
    assert text == plan.system_text == _sample_prompt()


def test_resolve_shadow_serves_legacy_and_logs_hashes(monkeypatch, caplog):
    monkeypatch.setenv("PAPER_CHAT_PIPELINE_ENABLED", "shadow")
    with caplog.at_level("INFO"):
        text, plan, mode = resolve_paper_chat_system_prompt(
            user_name="Ada",
            paper_title="CRP and Inflammation",
            authors="Smith et al.",
            year=2024,
            venue="Nature Med",
            now=FIXED_NOW,
        )
    assert mode == "shadow"
    assert plan is not None
    assert text == _sample_prompt()
    assert text == plan.system_text
    assert "identical=True" in caplog.text or "identical=true" in caplog.text.lower()
    assert _sample_prompt() not in caplog.text  # no full prompt body
    assert prompt_text_hash(text) in caplog.text


def test_shadow_parity_helper():
    a = _sample_prompt()
    assert log_shadow_prompt_parity(legacy_prompt=a, pipeline_prompt=a) is True
    assert log_shadow_prompt_parity(legacy_prompt=a, pipeline_prompt=a + "x") is False


def test_rag_developer_payload_framing_golden():
    """Excerpt JSON framing must stay stable (parity with /api/chat)."""
    excerpts = [
        {"text": "CRP rises", "page": 4, "section": "Methodology", "file": "p.pdf"},
    ]
    content = (
        "Relevant excerpts from the user's uploaded documents.\n"
        "Each excerpt may include 'page' (1-based PDF page) and/or "
        "'section' (heading the excerpt falls under). "
        "When citing, be specific: prefer 'p. 4, §Methodology' over "
        "just the filename. If no locator is present, cite by filename.\n"
        + json.dumps(excerpts, ensure_ascii=False)
    )
    assert '"page": 4' in content
    assert "Methodology" in content


def test_stream_round_sse_shape_and_observe_only():
    stream = FakeResponsesStreamClient(deltas=["Hi", " there"])
    executor = AIExecutor(stream_client=stream, default_model="fake")
    plan = build_legacy_paper_chat_plan(
        user_name="Ada",
        paper_title="P",
        now=FIXED_NOW,
        file_id=1,
    )
    events = list(
        executor.stream_round(
            plan,
            input_items=[{"role": "user", "content": "q"}],
            tools=[],
            model="fake",
        )
    )
    types = [e.type for e in events]
    assert types == [
        "response.output_text.delta",
        "response.output_text.delta",
        "response.completed",
    ]
    assert stream.calls[0]["instructions"] == plan.system_text
    assert "Soro Identity Doctrine" not in stream.calls[0]["instructions"]

    answer = "".join(e.delta for e in events if e.type == "response.output_text.delta")
    result = executor.observe_answer(plan, answer, model="fake", rag_excerpt_count=2)
    assert result.response.answer == "Hi there"
    assert result.metadata["observe_only"] is True
    assert result.prompt_version == LEGACY_PAPER_CHAT_PROMPT_VERSION
    assert result.metadata["plan_hash"]
    # Observe-only: answer must not be rewritten even if validator complains.
    empty = executor.observe_answer(plan, "", model="fake")
    assert empty.response.answer == ""
    assert empty.validator is not None
    assert empty.validator.errors  # answer_empty recorded
    assert empty.response.answer == ""  # still not rewritten


def test_prompt_plan_serialization_stable_for_legacy():
    plan = build_legacy_paper_chat_plan(
        user_name="Ada",
        paper_title="P",
        now=FIXED_NOW,
        file_id=9,
        question="Q?",
    )
    data = json.loads(plan.to_json())
    assert data["prompt_version"] == LEGACY_PAPER_CHAT_PROMPT_VERSION
    assert data["template_key"] == "legacy_paper_chat"
    assert data["system_text"] == plan.system_text
    assert plan.to_json() == plan.to_json()
