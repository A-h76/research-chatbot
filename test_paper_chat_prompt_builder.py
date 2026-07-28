"""Paper chat PromptBuilder + Phase 1 context wiring.

Run: pytest test_paper_chat_prompt_builder.py -v
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

import server
from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt


FIXED_NOW = datetime(2026, 7, 26, 15, 30, 0)


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


def test_build_paper_chat_system_prompt_matches_legacy(monkeypatch):
    monkeypatch.setenv("PAPER_CHAT_USE_PROMPT_BUILDER", "true")
    user = SimpleNamespace(name="Ada")
    paper = SimpleNamespace(
        title="CRP and Inflammation",
        name="file.pdf",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
    )
    system, phase1 = server.build_paper_chat_system_prompt(user, paper, now=FIXED_NOW)
    assert phase1 == ""
    assert system == render_legacy_paper_chat_prompt(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
        now=FIXED_NOW,
    )


def test_build_paper_chat_system_prompt_keeps_phase1_separate(monkeypatch):
    monkeypatch.setenv("PAPER_CHAT_USE_PROMPT_BUILDER", "true")
    user = SimpleNamespace(name="Ada")
    paper = SimpleNamespace(
        title="Paper",
        name="p.pdf",
        authors=None,
        year=None,
        venue=None,
    )
    block = "=== Phase 1 Structured Analysis ===\n- domain: ai"
    system, phase1 = server.build_paper_chat_system_prompt(
        user, paper, now=FIXED_NOW, phase1_context=block
    )
    assert phase1 == block
    assert "Phase 1" not in system
    assert system == render_legacy_paper_chat_prompt(
        user_name="Ada", paper_title="Paper", now=FIXED_NOW
    )


def test_load_paper_phase1_context_empty_when_disabled(db, monkeypatch):
    monkeypatch.setenv("PAPER_CHAT_PHASE1_CONTEXT", "false")
    assert server._load_paper_phase1_context(db, 1) == ""


def test_load_paper_phase1_context_from_row(db, monkeypatch):
    monkeypatch.setenv("PAPER_CHAT_PHASE1_CONTEXT", "true")
    user = server.User(email=f"pc-{server.uuid.uuid4().hex[:8]}@ex.com", name="T", auth_provider="dev")
    db.add(user)
    db.commit()
    uf = server.UserFile(
        user_id=user.id,
        name="p.pdf",
        mime="application/pdf",
        kind="document",
        path="x",
        size=1,
    )
    db.add(uf)
    db.commit()
    db.add(
        server.AnalysisPipelineResult(
            file_id=uf.id,
            user_id=user.id,
            status="done",
            phase_results='{"classification":{"domain":{"label":"medical","confidence":0.9}}}',
            content_hash="abc",
        )
    )
    db.commit()

    ctx = server._load_paper_phase1_context(db, uf.id)
    assert "Phase 1 Structured Analysis" in ctx
    assert "medical" in ctx
