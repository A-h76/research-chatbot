"""Tests for mode-composed Assistant prompt layers (ADR-0018)."""

from backend.assistant.prompt_layers import (
    compose_assistant_layers,
    format_research_state_block,
)
from backend.assistant.research_state import (
    CorpusSignals,
    ProjectSignals,
    UserSignals,
    WritingSignals,
    build_research_state,
    research_state_to_dict,
)


def test_compose_includes_base_and_mode():
    text = compose_assistant_layers(mode="teacher", intent="learning_task")
    assert "Dhund Assistant (decision context)" in text
    assert "Mode: Teacher" in text
    assert "capability list" in text.lower() or "Do NOT open with a capability" in text
    assert "Intent: learning_task" in text


def test_compose_research_state_numbers():
    state = build_research_state(
        user=UserSignals(experience="beginner", goals=("lit_review",), fields=("ai",)),
        project=ProjectSignals(id=12, title="AI in Healthcare"),
        corpus=CorpusSignals(papers=9, evidence=0, themes=0, gaps=0),
        writing=WritingSignals(),
    )
    text = compose_assistant_layers(
        mode="coach",
        research_state=research_state_to_dict(state),
        intent="workflow",
    )
    assert 'Project: "AI in Healthcare"' in text
    assert "papers=9" in text
    assert "evidence=0" in text
    assert "Extract evidence" in text or "next action" in text.lower()
    assert "beginner" in text.lower()


def test_expert_adaptation_terse():
    state = {
        "user": {"experience": "expert", "goals": [], "fields": []},
        "project": {"id": 1, "title": "X"},
        "corpus": {"papers": 9, "evidence": 100, "themes": 3, "gaps": 1, "contradictions": 0},
        "workflow": {
            "stage": "synthesis",
            "label": "Synthesis",
            "nextAction": {"id": "review_gaps", "label": "Review research gaps", "href": "/g"},
            "blockers": [],
        },
        "writing": {"hasManuscript": False, "reviewComplete": False},
    }
    text = compose_assistant_layers(mode="research_partner", research_state=state)
    assert "advanced/expert" in text or "terse" in text


def test_format_state_block_empty():
    assert format_research_state_block(None) == ""
    assert format_research_state_block({}) == ""
