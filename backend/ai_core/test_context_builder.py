"""ResearchContextBuilder orchestration — retrieve → rank → compress."""

from __future__ import annotations

from backend.ai_core.context import (
    ContextCompression,
    ContextRanking,
    ContextRetrieval,
    ResearchContextBuilder,
    RetrievedBundle,
)


from backend.ai_core.schemas.research_context import ResearchIntent


class _FakeRetrieval(ContextRetrieval):
    def retrieve(self, *, file_id=None, project_id=None, question=None, **_):
        return RetrievedBundle(
            document={"title": "Paper A"},
            entities=[{"id": "e1", "name": "Drug X"}] * 5,
            evidence=[{"id": f"ev-{i}"} for i in range(50)],
            notes=[{"id": "n1"}],
            citations=[{"id": "c1"}],
            passages=[{"text": "passage"}] * 20,
            meta={"file_id": file_id},
        )


def test_builder_pipeline_returns_pure_context():
    ctx = ResearchContextBuilder(
        retrieval=_FakeRetrieval(),
        ranking=ContextRanking(default_limit=10),
        compression=ContextCompression(max_evidence=8, max_passages=5),
    ).build(intent=ResearchIntent.WRITING, question="Draft limits", file_id=42)

    assert ctx.intent is ResearchIntent.WRITING
    assert ctx.file_id == 42
    assert ctx.document == {"title": "Paper A"}
    assert len(ctx.evidence) == 8
    assert len(ctx.extras["passages"]) == 5
    assert all(isinstance(e, dict) for e in ctx.entities)
    # No ORM-shaped objects
    assert not hasattr(ctx.entities[0], "_sa_instance_state")


def test_default_builder_empty_stub_runs():
    ctx = ResearchContextBuilder().build(intent=ResearchIntent.READING, file_id=1)
    assert ctx.intent is ResearchIntent.READING
    assert ctx.entities == []
    assert ctx.extras["retrieval_meta"]["source"] == "empty_stub"
