"""Rank / filter a ``RetrievedBundle`` for an intent + question.

Sprint 3: pass-through with optional list caps. Real scoring lands later.
"""

from __future__ import annotations

from dataclasses import replace

from backend.ai_core.context.bundle import RetrievedBundle
from backend.ai_core.schemas.research_context import ResearchIntent


class ContextRanking:
    """Intent-aware ranking over pure dict payloads."""

    def __init__(self, *, default_limit: int = 20) -> None:
        self._default_limit = default_limit

    def rank(
        self,
        bundle: RetrievedBundle,
        *,
        intent: ResearchIntent,
        question: str | None = None,
        limit: int | None = None,
    ) -> RetrievedBundle:
        cap = self._default_limit if limit is None else limit
        # Pass-through ranking: preserve order, cap list fields only.
        return replace(
            bundle,
            entities=list(bundle.entities[:cap]),
            evidence=list(bundle.evidence[:cap]),
            notes=list(bundle.notes[:cap]),
            citations=list(bundle.citations[:cap]),
            passages=list(bundle.passages[:cap]),
            meta={
                **bundle.meta,
                "ranked_for_intent": intent,
                "rank_question": question,
                "rank_limit": cap,
            },
        )


def rank_for_intent(
    items: list[dict],
    *,
    intent: ResearchIntent,
    question: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Rank a flat list (helper). Prefer ``ContextRanking.rank`` on a bundle."""
    return list(items[:limit])
