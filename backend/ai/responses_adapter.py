"""OpenAI Responses API adapter — owned by AI Gateway (Evolution Bite 2).

Feature routes must not call ``openai.OpenAI.responses`` directly. Chat and
paper streaming go through ``AIGateway.stream_responses`` / ``create_responses``,
which delegate here.

Reuses ``ResponsesStreamEvent`` from ai_core for compatibility with
``AIExecutor.stream_round``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from backend.ai_core.orchestration.responses_stream import (
    FakeResponsesStreamClient,
    OpenAIResponsesStreamClient,
    ResponsesStreamEvent,
)

__all__ = [
    "FakeResponsesAdapter",
    "FakeResponsesStreamClient",
    "OpenAIResponsesAdapter",
    "OpenAIResponsesStreamClient",
    "ResponsesStreamEvent",
]


class OpenAIResponsesAdapter:
    """Gateway-bound Responses transport (stream + non-stream)."""

    def __init__(self, openai_client: Any) -> None:
        self._client = openai_client
        self._stream_client = OpenAIResponsesStreamClient(openai_client)

    def stream(
        self,
        *,
        model: str,
        instructions: str,
        input: list[Any],
        tools: list[Any] | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Iterator[ResponsesStreamEvent]:
        yield from self._stream_client.stream(
            model=model,
            instructions=instructions,
            input=input,
            tools=tools,
            temperature=temperature,
            reasoning=reasoning,
            **kwargs,
        )

    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: list[Any],
        tools: list[Any] | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        create_kwargs: dict[str, Any] = dict(
            model=model,
            instructions=instructions,
            input=input,
            store=False,
            tools=tools or [],
            **kwargs,
        )
        if temperature is not None:
            create_kwargs["temperature"] = temperature
        if reasoning is not None:
            create_kwargs["reasoning"] = reasoning
        return self._client.responses.create(**create_kwargs)


@dataclass
class FakeResponsesAdapter:
    """Test double for gateway-owned Responses transport."""

    stream_client: FakeResponsesStreamClient = field(default_factory=FakeResponsesStreamClient)
    create_calls: list[dict[str, Any]] = field(default_factory=list)
    fail_create_message: str | None = None

    def stream(
        self,
        *,
        model: str,
        instructions: str,
        input: list[Any],
        tools: list[Any] | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Iterator[ResponsesStreamEvent]:
        yield from self.stream_client.stream(
            model=model,
            instructions=instructions,
            input=input,
            tools=tools,
            temperature=temperature,
            reasoning=reasoning,
            **kwargs,
        )

    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: list[Any],
        tools: list[Any] | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        self.create_calls.append(
            {
                "model": model,
                "instructions": instructions,
                "input": input,
                "tools": tools,
                "temperature": temperature,
                "reasoning": reasoning,
                "kwargs": kwargs,
            }
        )
        if self.fail_create_message:
            raise RuntimeError(self.fail_create_message)

        class _Usage:
            input_tokens = 12
            output_tokens = 8

        class _Final:
            output: list[Any] = []
            usage = _Usage()

        return _Final()
