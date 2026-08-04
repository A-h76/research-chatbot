"""Research Scope Prompt Gateway tests."""

from __future__ import annotations

from backend.ai.research_scope import (
    RS_VERSION,
    ScopeVerdict,
    evaluate_research_scope,
    enforcement_mode,
)


def test_version():
    assert RS_VERSION == "1.0"


def test_redirect_add_two_numbers():
    d = evaluate_research_scope("write python code adding 2 numbers")
    assert d.verdict == ScopeVerdict.REDIRECT
    assert d.blocks_llm
    assert "research" in d.user_message.lower()
    assert "declined" not in d.user_message.lower()
    assert d.relevance_score is not None and d.relevance_score < 40


def test_allow_pandas_experiment():
    d = evaluate_research_scope(
        "Write Python with pandas to analyze this CSV from my experiment and plot the ROC curve"
    )
    assert d.verdict == ScopeVerdict.ALLOW
    assert d.relevance_score and d.relevance_score > 70


def test_allow_anova():
    d = evaluate_research_scope("Explain ANOVA for my methods section")
    assert d.verdict == ScopeVerdict.ALLOW


def test_allow_workflow_support():
    assert evaluate_research_scope("Translate this Spanish abstract").verdict == ScopeVerdict.ALLOW
    assert (
        evaluate_research_scope("Improve the grammar of this paragraph for my manuscript").verdict
        == ScopeVerdict.ALLOW
    )


def test_allow_latex():
    d = evaluate_research_scope("Help me write LaTeX for my manuscript table")
    assert d.verdict == ScopeVerdict.ALLOW


def test_clarify_ambiguous_python_with_project():
    d = evaluate_research_scope("Write Python.", project_name="Osteoarthritis")
    assert d.verdict == ScopeVerdict.CLARIFY
    assert "Osteoarthritis" in d.user_message
    assert d.relevance_score and 40 <= d.relevance_score <= 70


def test_paper_scoped_always_allow():
    d = evaluate_research_scope("summarize section 3", paper_scoped=True)
    assert d.verdict == ScopeVerdict.ALLOW


def test_research_skill_allows():
    d = evaluate_research_scope("compare these", research_skill="compare")
    assert d.verdict == ScopeVerdict.ALLOW


def test_redirect_entertainment_and_lifestyle():
    poem = evaluate_research_scope("Write a birthday poem", project_name="Osteoarthritis")
    assert poem.verdict == ScopeVerdict.REDIRECT
    joke = evaluate_research_scope("Tell me a joke")
    assert joke.verdict == ScopeVerdict.REDIRECT
    vac = evaluate_research_scope("Plan my vacation to Bali")
    assert vac.verdict == ScopeVerdict.REDIRECT


def test_allow_research_coding_kaplan_meier():
    d = evaluate_research_scope(
        "Write Python code to perform a Kaplan-Meier survival analysis on this dataset"
    )
    assert d.verdict == ScopeVerdict.ALLOW


def test_redirect_copy_is_purposeful_not_censorship():
    d = evaluate_research_scope("Tell me a joke", project_name="Soil carbon")
    assert d.verdict == ScopeVerdict.REDIRECT
    msg = d.user_message.lower()
    assert "declined" not in msg
    assert "access denied" not in msg
    assert "literature review" in msg or "manuscript" in msg or "paper" in msg


def test_system_verdict_is_internal():
    from backend.ai.research_scope import system_scope_decision

    d = system_scope_decision("upload")
    assert d.verdict == ScopeVerdict.SYSTEM
    assert not d.blocks_llm
    assert not d.is_user_facing


def test_enforcement_off(monkeypatch):
    monkeypatch.setenv("RESEARCH_SCOPE_ENFORCEMENT", "off")
    assert enforcement_mode() == "off"
    d = evaluate_research_scope("write python adding 2 numbers")
    assert d.verdict == ScopeVerdict.ALLOW
