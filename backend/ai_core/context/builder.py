"""ResearchContextBuilder — orchestrate retrieve → rank → compress → ResearchContext.

No SQLAlchemy models cross this boundary. Retrieval adapters (later) must
convert ORM rows into pure dicts inside ``ContextRetrieval`` before returning
a ``RetrievedBundle``.
"""

from __future__ import annotations

from backend.ai_core.context.bundle import RetrievedBundle
from backend.ai_core.context.compression import ContextCompression
from backend.ai_core.context.ranking import ContextRanking
from backend.ai_core.context.retrieval import ContextRetrieval
from backend.ai_core.schemas.research_context import ResearchContext, ResearchIntent


class ResearchContextBuilder:
    """Assemble a slim, intent-filtered ``ResearchContext``.

    Pipeline::

        Retrieval → Ranking → Compression → ResearchContext

    Example::

        context = ResearchContextBuilder().build(
            file_id=file_id,
            intent="writing",
            question=user_question,
        )
    """

    def __init__(
        self,
        *,
        retrieval: ContextRetrieval | None = None,
        ranking: ContextRanking | None = None,
        compression: ContextCompression | None = None,
    ) -> None:
        self._retrieval = retrieval or ContextRetrieval()
        self._ranking = ranking or ContextRanking()
        self._compression = compression or ContextCompression()

    def build(
        self,
        *,
        intent: ResearchIntent | str,
        question: str | None = None,
        file_id: int | None = None,
        project_id: int | None = None,
        **_: object,
    ) -> ResearchContext:
        resolved = intent if isinstance(intent, ResearchIntent) else ResearchIntent(intent)
        raw = self._retrieval.retrieve(
            file_id=file_id,
            project_id=project_id,
            question=question,
        )
        ranked = self._ranking.rank(raw, intent=resolved, question=question)
        compressed = self._compression.compress(
            ranked,
            intent=resolved,
            question=question,
        )
        return self._to_research_context(
            compressed,
            intent=resolved,
            question=question,
            file_id=file_id,
            project_id=project_id,
        )

    @staticmethod
    def _to_research_context(
        bundle: RetrievedBundle,
        *,
        intent: ResearchIntent,
        question: str | None,
        file_id: int | None,
        project_id: int | None,
    ) -> ResearchContext:
        return ResearchContext(
            intent=intent,
            question=question,
            file_id=file_id,
            project_id=project_id,
            document=dict(bundle.document),
            classification=dict(bundle.classification),
            entities=list(bundle.entities),
            evidence=list(bundle.evidence),
            graph=dict(bundle.graph),
            narrative=dict(bundle.narrative),
            notes=list(bundle.notes),
            citations=list(bundle.citations),
            extras={
                "passages": list(bundle.passages),
                "retrieval_meta": dict(bundle.meta),
            },
        )
