"""Intent-scoped context assembly.

Pipeline: ``ResearchContextBuilder`` → Retrieval → Ranking → Compression → ``ResearchContext``.

``Phase1Retrieval`` lives in ``phase1_retrieval`` (import from there) to avoid
adapter ↔ context circular imports. See ADR-0002.
"""

from backend.ai_core.context.builder import ResearchContextBuilder
from backend.ai_core.context.bundle import RetrievedBundle
from backend.ai_core.context.compression import ContextCompression
from backend.ai_core.context.ranking import ContextRanking
from backend.ai_core.context.retrieval import ContextRetrieval

__all__ = [
    "ContextCompression",
    "ContextRanking",
    "ContextRetrieval",
    "ResearchContextBuilder",
    "RetrievedBundle",
]
