"""Inbound AI call contract — feature routes build this, not OpenAI kwargs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.ai_core.schemas.research_context import ResearchIntent


@dataclass(frozen=True)
class AIRequest:
    """Feature-facing request into the ai_core pipeline."""

    question: str
    intent: ResearchIntent | None = None
    file_id: int | None = None
    project_id: int | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
