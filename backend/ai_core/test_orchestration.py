"""Sprint 3 — PromptRouter + ResponseValidator (+ heuristic IntentClassifier)."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from backend.ai_core.context import ResearchContextBuilder, RetrievedBundle, ContextRetrieval
from backend.ai_core.identity import IdentityLoader
from backend.ai_core.orchestration import (
    IntentClassifier,
    PromptRouter,
    ResponseValidator,
)
from backend.ai_core.orchestration.prompt_router import PromptPlan
from backend.ai_core.schemas.ai_response import AIResponse, EvidenceReference
from backend.ai_core.schemas.research_context import ResearchContext, ResearchIntent
from backend.ai_core.schemas.workspace_reference import WorkspaceReference
from backend.ai_core.versions import LEGACY_PAPER_CHAT_PROMPT_VERSION


class _RichRetrieval(ContextRetrieval):
    def retrieve(self, *, file_id=None, project_id=None, question=None, **_):
        return RetrievedBundle(
            entities=[{"id": "ent-1", "name": "inflammation"}],
            evidence=[{"id": "ev-1", "label": "CRP elevation"}],
            meta={"file_id": file_id},
        )


def test_intent_classifier_hint_and_keywords():
    clf = IntentClassifier()
    assert clf.classify("anything", hint=ResearchIntent.READING) is ResearchIntent.READING
    assert clf.classify("Compare these two RCTs") is ResearchIntent.COMPARE
    assert clf.classify("Summarise the methods") is ResearchIntent.READING
    assert clf.classify("What year was it published?") is ResearchIntent.QUESTION


def test_prompt_router_uses_identity_loader_di():
    loader = IdentityLoader()
    context = ResearchContextBuilder(retrieval=_RichRetrieval()).build(
        file_id=42,
        intent=ResearchIntent.READING,
        question="Summarise the evidence for inflammation.",
    )
    plan = PromptRouter(identity_loader=loader).route(
        ResearchIntent.READING,
        context,
        question="Summarise the evidence for inflammation.",
    )
    assert plan.template_key == "reading"
    assert plan.intent is ResearchIntent.READING
    assert "Dhund Identity Doctrine" in plan.system_text
    assert "inflammation" in plan.context_text
    messages = plan.messages()
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert plan.metadata["evidence_count"] == 1


def test_prompt_plan_frozen_and_metadata_immutable():
    plan = PromptPlan(
        intent=ResearchIntent.READING,
        template_key="legacy_paper_chat",
        system_text="SYSTEM",
        skill_text="SKILL",
        context_text="{}",
        question="Q?",
        prompt_version=LEGACY_PAPER_CHAT_PROMPT_VERSION,
        metadata={"file_id": 42},
    )
    with pytest.raises(FrozenInstanceError):
        plan.template_key = "mutated"  # type: ignore[misc]
    with pytest.raises(TypeError):
        plan.metadata["file_id"] = 99  # type: ignore[index]


def test_prompt_plan_to_json_matches_fixture():
    """Deterministic serialization protects router ↔ executor interface."""
    plan = PromptPlan(
        intent=ResearchIntent.READING,
        template_key="legacy_paper_chat",
        system_text="SYSTEM",
        skill_text="SKILL",
        context_text="{}",
        question="Q?",
        identity_version="1.0.0",
        prompt_version=LEGACY_PAPER_CHAT_PROMPT_VERSION,
        context_schema_version="2.0.0",
        metadata={"file_id": 42},
    )
    expected = (
        '{"context_schema_version":"2.0.0",'
        '"context_text":"{}",'
        '"identity_version":"1.0.0",'
        '"intent":"reading",'
        '"metadata":{"file_id":42},'
        f'"prompt_version":"{LEGACY_PAPER_CHAT_PROMPT_VERSION}",'
        '"question":"Q?",'
        '"skill_text":"SKILL",'
        '"system_text":"SYSTEM",'
        '"template_key":"legacy_paper_chat"}'
    )
    assert plan.to_json() == expected
    assert plan.to_json() == plan.to_json()
    assert json.loads(plan.to_json())["prompt_version"] == LEGACY_PAPER_CHAT_PROMPT_VERSION


def test_legacy_paper_chat_prompt_version_constant():
    assert LEGACY_PAPER_CHAT_PROMPT_VERSION == "legacy_paper_chat_v1"


def test_response_validator_ok_and_errors():
    v = ResponseValidator()
    ok = v.validate(
        AIResponse(
            answer="CRP rises with inflammation.",
            confidence="Medium",
            evidence=[EvidenceReference(id="ev-1", label="CRP")],
            limitations=["Single paper"],
            workspace_refs=[
                WorkspaceReference(
                    id="wr-1",
                    kind="evidence.outcome",
                    ref_id="ev-1",
                    tab="evidence",
                )
            ],
        )
    )
    assert ok.ok and ok.response is not None
    assert not ok.errors

    bad = v.validate({"answer": "", "confidence": "Nope"})
    assert not bad.ok
    assert "answer_empty" in bad.errors
    assert any(e.startswith("confidence_invalid") for e in bad.errors)


def test_full_chain_without_routes():
    """IdentityLoader → ContextBuilder → PromptRouter → ResponseValidator."""
    question = "Summarise the evidence for inflammation."
    intent = IntentClassifier().classify(question, hint=ResearchIntent.READING)
    context = ResearchContextBuilder(retrieval=_RichRetrieval()).build(
        file_id=42,
        intent=intent,
        question=question,
    )
    assert context.intent is ResearchIntent.READING
    assert len(context.evidence) > 0
    assert len(context.entities) > 0

    plan = PromptRouter(identity_loader=IdentityLoader()).route(
        intent, context, question=question
    )
    # Simulated model output — validator is the gate, not OpenAI.
    result = ResponseValidator().validate(
        AIResponse(
            answer="Evidence links inflammation markers to the outcome.",
            confidence="Medium",
            evidence=[EvidenceReference(id="ev-1", label="CRP elevation")],
            limitations=["Stub retrieval — not live Phase 1 yet"],
        )
    )
    assert result.ok
    assert plan.metadata["file_id"] == 42
