"""OpenAI Responses API streaming client (Stage 1 Paper Chat).

Only ``AIExecutor`` (and tests) should use this — routes must not call the
SDK directly on the Stage 1 pipeline path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol


@dataclass(frozen=True)
class ResponsesStreamEvent:
    """Provider-neutral Responses stream event."""

    type: str
    delta: str = ""
    response: Any = None
    error_message: str | None = None
    usage: Any = None


class ResponsesStreamClient(Protocol):
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
    ) -> Iterator[ResponsesStreamEvent]: ...


@dataclass
class FakeResponsesStreamClient:
    """Deterministic stream for SSE-shape / contract tests."""

    deltas: list[str] = field(default_factory=lambda: ["Hello", " world"])
    model: str = "fake-responses"
    calls: list[dict[str, Any]] = field(default_factory=list)
    fail_message: str | None = None

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
        self.calls.append(
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
        if self.fail_message:
            yield ResponsesStreamEvent(type="response.failed", error_message=self.fail_message)
            return
        for delta in self.deltas:
            yield ResponsesStreamEvent(type="response.output_text.delta", delta=delta)

        class _Usage:
            input_tokens = 11
            output_tokens = 7
            total_tokens = 18

        class _Final:
            output: list[Any] = []
            usage = _Usage()

        yield ResponsesStreamEvent(type="response.completed", response=_Final(), usage=_Usage())


class OpenAIResponsesStreamClient:
    """Thin adapter around ``openai.OpenAI.responses.create(stream=True)``."""

    def __init__(self, client: Any) -> None:
        self._client = client

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
        create_kwargs: dict[str, Any] = dict(
            model=model,
            instructions=instructions,
            input=input,
            stream=True,
            store=False,
            tools=tools or [],
            **kwargs,
        )
        if temperature is not None:
            create_kwargs["temperature"] = temperature
        if reasoning is not None:
            create_kwargs["reasoning"] = reasoning

        stream = self._client.responses.create(**create_kwargs)
        for event in stream:
            et = getattr(event, "type", "") or ""
            if et == "response.output_text.delta":
                yield ResponsesStreamEvent(
                    type=et,
                    delta=getattr(event, "delta", "") or "",
                )
            elif et == "response.completed":
                resp = getattr(event, "response", None)
                yield ResponsesStreamEvent(
                    type=et,
                    response=resp,
                    usage=getattr(resp, "usage", None) if resp is not None else None,
                )
            elif et == "response.failed":
                err = getattr(getattr(event, "response", None), "error", None)
                msg = getattr(err, "message", None) or "response failed"
                yield ResponsesStreamEvent(type=et, error_message=str(msg), response=getattr(event, "response", None))
