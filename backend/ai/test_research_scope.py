"""Research Scope Prompt Gateway tests."""

from __future__ import annotations

import os

from backend.ai.research_scope import (
    RS_VERSION,
    ScopeVerdict,
    evaluate_research_scope,
    enforcement_mode,
)


def test_version():
    assert RS_VERSION == "0.1"


def test_decline_add_two_numbers():
    d = evaluate_research_scope("write python code adding 2 numbers")
    assert d.verdict == ScopeVerdict.DECLINE
    assert d.blocks_llm
    assert "research" in d.user_message.lower()


def test_allow_pandas_experiment():
    d = evaluate_research_scope(
        "Write Python with pandas to analyze this CSV from my experiment and plot the ROC curve"
    )
    assert d.verdict == ScopeVerdict.ALLOW


def test_allow_anova():
    d = evaluate_research_scope("Explain ANOVA for my methods section")
    assert d.verdict == ScopeVerdict.ALLOW


def test_allow_latex():
    d = evaluate_research_scope("Help me write LaTeX for my manuscript table")
    assert d.verdict == ScopeVerdict.ALLOW


def test_clarify_ambiguous_python_with_project():
    d = evaluate_research_scope("Write Python.", project_name="Osteoarthritis")
    assert d.verdict == ScopeVerdict.CLARIFY
    assert "Osteoarthritis" in d.user_message


def test_paper_scoped_always_allow():
    d = evaluate_research_scope("summarize section 3", paper_scoped=True)
    assert d.verdict == ScopeVerdict.ALLOW


def test_research_skill_allows():
    d = evaluate_research_scope("compare these", research_skill="compare")
    assert d.verdict == ScopeVerdict.ALLOW


def test_enforcement_off(monkeypatch):
    monkeypatch.setenv("RESEARCH_SCOPE_ENFORCEMENT", "off")
    assert enforcement_mode() == "off"
    d = evaluate_research_scope("write python adding 2 numbers")
    assert d.verdict == ScopeVerdict.ALLOW
