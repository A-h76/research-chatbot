"""Validation outcome — kept in schemas to avoid orchestration circular imports."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.ai_core.schemas.ai_response import AIResponse


@dataclass
class ValidationResult:
    """Outcome of validating an AI response."""

    ok: bool
    response: AIResponse | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
