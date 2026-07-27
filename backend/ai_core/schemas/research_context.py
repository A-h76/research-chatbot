"""Intent-scoped research context assembled for a single AI call.

**Purity rule:** ``ResearchContext`` must never hold SQLAlchemy (or other ORM)
instances. All nested values are JSON-friendly: ``dict``, ``list``, ``str``,
``int``, ``float``, ``bool``, ``None``. Convert at the retrieval boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResearchIntent(str, Enum):
    """Shared intents for classifier, context builder, and prompt router."""

    QUESTION = "question"
    READING = "reading"
    COMPARE = "compare"
    WRITING = "writing"
    CRITIQUE = "critique"
    EXPLAIN = "explain"
    REVIEW = "review"
    GAP_ANALYSIS = "gap_analysis"
    CITATION = "citation"
    OUTLINE = "outline"
    UNKNOWN = "unknown"


@dataclass
class ResearchContext:
    """Slim, intent-filtered context — pure data only (no ORM)."""

    intent: ResearchIntent
    question: str | None = None
    file_id: int | None = None
    project_id: int | None = None
    document: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] = field(default_factory=dict)
    entities: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    graph: dict[str, Any] = field(default_factory=dict)
    narrative: dict[str, Any] = field(default_factory=dict)
    notes: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
