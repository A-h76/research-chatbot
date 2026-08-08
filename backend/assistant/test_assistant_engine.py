"""Unit tests for Assistant Engine Research State + intent (no DB)."""

from backend.assistant.engine import AssistantEngine
from backend.assistant.intent import classify_intent, select_mode
from backend.assistant.research_state import (
    CorpusSignals,
    ProjectSignals,
    WritingSignals,
    UserSignals,
    build_research_state,
    derive_next_action,
    derive_stage,
    research_state_to_dict,
    STAGE_DISCOVERY,
    STAGE_EVIDENCE,
    STAGE_LIBRARY,
    STAGE_SYNTHESIS,
    STAGE_WRITING,
)


def test_stage_no_project():
    assert (
        derive_stage(CorpusSignals(), WritingSignals(), has_project=False) == STAGE_DISCOVERY
    )


def test_stage_library_then_evidence():
    assert (
        derive_stage(CorpusSignals(papers=0), WritingSignals(), has_project=True)
        == STAGE_LIBRARY
    )
    assert (
        derive_stage(CorpusSignals(papers=9, evidence=0), WritingSignals(), has_project=True)
        == STAGE_EVIDENCE
    )


def test_stage_synthesis_and_writing():
    assert (
        derive_stage(
            CorpusSignals(papers=9, evidence=10),
            WritingSignals(has_manuscript=False),
            has_project=True,
        )
        == STAGE_SYNTHESIS
    )
    assert (
        derive_stage(
            CorpusSignals(papers=9, evidence=10),
            WritingSignals(has_manuscript=True),
            has_project=True,
        )
        == STAGE_WRITING
    )


def test_next_action_extract_evidence():
    na = derive_next_action(
        CorpusSignals(papers=9, evidence=0),
        WritingSignals(),
        has_project=True,
    )
    assert na.id == "extract_evidence"


def test_greeting_is_local():
    intent = classify_intent("Hi")
    assert intent.kind == "greeting"
    assert intent.local_only is True
    assert select_mode(intent) == "companion"


def test_uncertain_is_coach():
    intent = classify_intent("I don't know")
    assert intent.kind == "uncertain"
    assert intent.local_only is True
    assert select_mode(intent) == "coach"


def test_learning_goes_to_llm():
    intent = classify_intent("What is YOLO?")
    assert intent.kind == "learning_task"
    assert intent.local_only is False
    assert select_mode(intent) == "teacher"


def test_engine_greeting_does_not_start_job():
    state = build_research_state(
        user=UserSignals(experience="beginner", display_name="Ahmad"),
        project=ProjectSignals(id=1, title="AI in Healthcare"),
        corpus=CorpusSignals(papers=9, evidence=0),
        writing=WritingSignals(),
    )

    def get_state(_uid, _pid=None):
        return state

    engine = AssistantEngine(get_state)
    out = engine.turn(user_id=1, message="Hi", project_id=1)
    assert out["outcome"] == "local_reply"
    assert out["mode"] == "companion"
    text = " ".join(out["local_reply"]["lines"])
    assert "AI in Healthcare" in text
    assert "Evidence hasn't been extracted" in text
    assert "Ask me anything" in text
    assert "Good to see you again" not in text
    assert out["local_reply"]["action_card"] is not None
    # Single next step — not a capability menu
    assert len(out["local_reply"]["action_card"]["actions"]) == 1


def test_open_session_restores_context_without_cta_card():
    state = build_research_state(
        user=UserSignals(experience="intermediate", display_name="Ahmad"),
        project=ProjectSignals(id=1, title="Artificial Intelligence in Healthcare"),
        corpus=CorpusSignals(papers=9, evidence=0),
        writing=WritingSignals(),
    )
    engine = AssistantEngine(lambda *_a, **_k: state)
    out = engine.open_session(user_id=1, project_id=1)
    text = " ".join(out["local_reply"]["lines"])
    assert "Artificial Intelligence in Healthcare" in text
    assert "Evidence hasn't been extracted" in text
    assert "Ask me anything about your research" in text
    assert out["local_reply"]["action_card"] is None


def test_engine_research_question_starts_job():
    state = build_research_state(
        user=UserSignals(experience="intermediate", display_name="Ahmad"),
        project=ProjectSignals(id=1, title="AI in Healthcare"),
        corpus=CorpusSignals(papers=9, evidence=12),
        writing=WritingSignals(),
    )

    engine = AssistantEngine(lambda *_a, **_k: state)
    out = engine.turn(user_id=1, message="What is federated learning?", project_id=1)
    assert out["outcome"] == "start_job"
    assert out["start_job"]["message"] == "What is federated learning?"


def test_research_state_dict_shape():
    state = build_research_state(
        user=UserSignals(experience="beginner", goals=("lit_review",), fields=("ai",)),
        project=ProjectSignals(id=12, title="Artificial Intelligence in Healthcare"),
        corpus=CorpusSignals(papers=9, evidence=342, themes=12, gaps=3, contradictions=3, coverage=0.92),
        writing=WritingSignals(has_manuscript=False),
    )
    d = research_state_to_dict(state)
    assert d["project"]["title"] == "Artificial Intelligence in Healthcare"
    assert d["corpus"]["papers"] == 9
    assert d["workflow"]["stage"] == STAGE_SYNTHESIS
    assert d["workflow"]["nextAction"]["id"] in {
        "review_gaps",
        "inspect_contradictions",
        "start_writing",
        "compare_papers",
    }
