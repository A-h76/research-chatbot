"""AIExecutor + versioning tests."""

from __future__ import annotations

from backend.ai_core.context import ResearchContextBuilder
from backend.ai_core.context.phase1_retrieval import MemoryPhase1Source, Phase1Retrieval
from backend.ai_core.identity import IdentityLoader
from backend.ai_core.orchestration import AIExecutor, FakeLLMClient, IntentClassifier, PromptRouter
from backend.ai_core.schemas.request import AIRequest
from backend.ai_core.schemas.research_context import ResearchIntent
from backend.ai_core.test_adapters import PHASE1_FIXTURE
from backend.ai_core.versions import (
    CONTEXT_SCHEMA_VERSION,
    IDENTITY_VERSION,
    LEGACY_PAPER_CHAT_PROMPT_VERSION,
    prompt_version_for,
)


def test_versions_are_independent():
    assert IDENTITY_VERSION
    assert CONTEXT_SCHEMA_VERSION
    assert prompt_version_for("reading") == "reading_v1"
    assert prompt_version_for("legacy_paper_chat") == LEGACY_PAPER_CHAT_PROMPT_VERSION
    assert IDENTITY_VERSION != CONTEXT_SCHEMA_VERSION


def test_executor_stamps_versions_and_usage():
    source = MemoryPhase1Source(phase_results_by_file={42: PHASE1_FIXTURE})
    request = AIRequest(
        question="Summarise the evidence for inflammation.",
        intent=ResearchIntent.READING,
        file_id=42,
    )
    intent = IntentClassifier().classify(request.question, hint=request.intent)
    context = ResearchContextBuilder(retrieval=Phase1Retrieval(source)).build(
        file_id=request.file_id,
        intent=intent,
        question=request.question,
    )
    plan = PromptRouter(identity_loader=IdentityLoader()).route(
        intent, context, question=request.question
    )
    assert plan.identity_version == IDENTITY_VERSION
    assert plan.prompt_version == "reading_v1"
    assert plan.context_schema_version == CONTEXT_SCHEMA_VERSION

    client = FakeLLMClient(text="CRP evidence supports inflammation involvement.")
    result = AIExecutor(client=client, default_model="gpt-4o-mini").execute(plan)

    assert result.response.answer
    assert result.usage.total_tokens == 18
    assert result.latency_ms >= 0
    assert result.model == "gpt-4o-mini"
    assert result.identity_version == IDENTITY_VERSION
    assert result.prompt_version == "reading_v1"
    assert result.context_schema_version == CONTEXT_SCHEMA_VERSION
    assert result.validator is not None
    assert len(client.calls) == 1


def test_executor_handles_client_failure_safely():
    class Boom:
        def complete(self, messages, *, model, **kwargs):
            raise RuntimeError("provider down")

    plan = PromptRouter(identity_loader=IdentityLoader()).route(
        ResearchIntent.QUESTION,
        ResearchContextBuilder().build(intent=ResearchIntent.QUESTION, question="Hi"),
        question="Hi",
    )
    result = AIExecutor(client=Boom()).execute(plan)  # type: ignore[arg-type]
    assert result.response.confidence == "Low"
    assert result.metadata.get("error")
    assert "failed" in " ".join(result.response.limitations).lower()
