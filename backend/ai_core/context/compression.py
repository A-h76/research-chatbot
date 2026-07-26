"""Compress a ranked bundle into a token-budget-friendly form.

Today: light caps / empty-field pruning.  
Tomorrow: token budgeting, dedupe, overlapping evidence removal, section
merging, citation collapsing, graph pruning — keep that growth here, not
in ``ResearchContextBuilder``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.ai_core.context.bundle import RetrievedBundle
from backend.ai_core.schemas.research_context import ResearchIntent


def _nonempty_dict(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


class ContextCompression:
    """Shrink ranked context for the model window."""

    def __init__(
        self,
        *,
        max_entities: int = 30,
        max_evidence: int = 20,
        max_notes: int = 10,
        max_citations: int = 15,
        max_passages: int = 12,
    ) -> None:
        self._max_entities = max_entities
        self._max_evidence = max_evidence
        self._max_notes = max_notes
        self._max_citations = max_citations
        self._max_passages = max_passages

    def compress(
        self,
        bundle: RetrievedBundle,
        *,
        intent: ResearchIntent,
        question: str | None = None,
    ) -> RetrievedBundle:
        return replace(
            bundle,
            document=_nonempty_dict(dict(bundle.document)),
            classification=_nonempty_dict(dict(bundle.classification)),
            entities=list(bundle.entities[: self._max_entities]),
            evidence=list(bundle.evidence[: self._max_evidence]),
            graph=_nonempty_dict(dict(bundle.graph)),
            narrative=_nonempty_dict(dict(bundle.narrative)),
            notes=list(bundle.notes[: self._max_notes]),
            citations=list(bundle.citations[: self._max_citations]),
            passages=list(bundle.passages[: self._max_passages]),
            meta={
                **bundle.meta,
                "compressed_for_intent": intent,
                "compress_question": question,
            },
        )
