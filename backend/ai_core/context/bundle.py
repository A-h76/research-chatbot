"""Pure retrieved context bag — no SQLAlchemy / ORM objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedBundle:
    """Boundary object between retrieval → ranking → compression.

    All fields are JSON-friendly primitives / dicts / lists of dicts.
    **Never** attach ORM instances here.
    """

    document: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] = field(default_factory=dict)
    entities: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    graph: dict[str, Any] = field(default_factory=dict)
    narrative: dict[str, Any] = field(default_factory=dict)
    notes: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    # Rankable snippets (chunk text, section excerpts, etc.)
    passages: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
