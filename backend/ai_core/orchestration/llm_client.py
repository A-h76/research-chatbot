"""LLM client boundary — only ``AIExecutor`` talks to providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.ai_core.schemas.execution import TokenUsage


@dataclass
class LLMCompletion:
    """Provider-neutral completion payload."""

    text: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    """Swap FakeLLMClient in tests; ModelRegistryLLMClient in production."""

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        **kwargs: Any,
    ) -> LLMCompletion: ...


class FakeLLMClient:
    """Deterministic client for unit tests — no network."""

    def __init__(self, text: str = "Grounded stub answer.", *, model: str = "fake-model") -> None:
        self._text = text
        self._model = model
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        **kwargs: Any,
    ) -> LLMCompletion:
        self.calls.append({"messages": messages, "model": model, "kwargs": kwargs})
        return LLMCompletion(
            text=self._text,
            model=model or self._model,
            usage=TokenUsage(prompt_tokens=11, completion_tokens=7, total_tokens=18),
            raw={"fake": True},
        )


class ModelRegistryLLMClient:
    """Adapter around ``backend.ai.ModelRegistry.call`` (Chat Completions)."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        **kwargs: Any,
    ) -> LLMCompletion:
        result = self._registry.call(model, messages, **kwargs)
        if isinstance(result, dict):
            text = str(result.get("content") or result.get("text") or "")
            usage_raw = result.get("usage") if isinstance(result.get("usage"), dict) else {}
            used_model = str(result.get("model") or model)
            return LLMCompletion(
                text=text,
                model=used_model,
                usage=TokenUsage.from_openai(usage_raw),
                raw=result,
            )
        return LLMCompletion(text=str(result), model=model, usage=TokenUsage())
