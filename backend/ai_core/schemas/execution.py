"""Execution-layer result — model call metadata separate from ``AIResponse``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.ai_core.schemas.ai_response import AIResponse
from backend.ai_core.schemas.validation import ValidationResult


@dataclass(frozen=True)
class TokenUsage:
    """Token accounting for one model invocation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_openai(cls, usage: dict[str, Any] | None) -> TokenUsage:
        if not usage:
            return cls()
        prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        return cls(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


@dataclass(frozen=True)
class AIExecutionResult:
    """Full execution envelope for cost / analytics / benchmarks.

    ``response`` is user-facing. Everything else is observability — do not
    fold usage/latency into ``AIResponse``.
    """

    response: AIResponse
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: int = 0
    model: str = ""
    prompt_version: str = ""
    identity_version: str = ""
    context_schema_version: str = ""
    validator: ValidationResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
