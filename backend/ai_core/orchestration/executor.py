"""AIExecutor — PromptPlan → LLM → AIExecutionResult.


Owns provider calls (via ``LLMClient`` / ``ResponsesStreamClient``), timing,

validation, and version stamps. Feature routes must not import OpenAI SDKs —

only this module (and its clients).


Stage 1 Paper Chat: ``stream_round`` drives Responses SSE; ``observe_answer``

is Observe → Record → Warn only (never rewrite / regenerate).

"""


from __future__ import annotations


import hashlib

import json

import logging

import time

from typing import Any, Iterator


from backend.ai_core.orchestration.llm_client import FakeLLMClient, LLMClient, LLMCompletion

from backend.ai_core.orchestration.prompt_router import PromptPlan

from backend.ai_core.orchestration.response_validator import ResponseValidator

from backend.ai_core.orchestration.responses_stream import (

    FakeResponsesStreamClient,

    ResponsesStreamClient,

    ResponsesStreamEvent,

)

from backend.ai_core.schemas.ai_response import AIResponse, EvidenceReference

from backend.ai_core.schemas.execution import AIExecutionResult, TokenUsage

from backend.ai_core.schemas.validation import ValidationResult

from backend.ai_core.schemas.workspace_reference import WorkspaceReference

from backend.ai_core.versions import (

    CONTEXT_SCHEMA_VERSION,

    IDENTITY_VERSION,

    prompt_version_for,

)


logger = logging.getLogger(__name__)


class AIExecutor:

    """Execute a ``PromptPlan`` and return a fully stamped ``AIExecutionResult``."""

    def __init__(

        self,

        client: LLMClient | None = None,

        *,

        stream_client: ResponsesStreamClient | None = None,

        validator: ResponseValidator | None = None,

        default_model: str = "gpt-4o-mini",

    ) -> None:

        self._client: LLMClient = client or FakeLLMClient()

        self._stream_client: ResponsesStreamClient = stream_client or FakeResponsesStreamClient()

        self._validator = validator or ResponseValidator()

        self._default_model = default_model

    def execute(

        self,

        plan: PromptPlan,

        *,

        model: str | None = None,

        **kwargs: Any,

    ) -> AIExecutionResult:

        used_model = model or self._default_model

        prompt_ver = plan.prompt_version or prompt_version_for(plan.template_key)

        identity_ver = plan.identity_version or IDENTITY_VERSION

        context_ver = plan.context_schema_version or CONTEXT_SCHEMA_VERSION

        started = time.perf_counter()

        error: str | None = None

        completion: LLMCompletion | None = None

        try:

            completion = self._client.complete(plan.messages(), model=used_model, **kwargs)

        except Exception as exc:

            logger.exception("AIExecutor LLM call failed")

            error = str(exc)

        latency_ms = int((time.perf_counter() - started) * 1000)

        if completion is None:

            response = AIResponse(

                answer="",

                confidence="Low",

                limitations=[f"Model call failed: {error or 'unknown'}"],

            )

            usage = TokenUsage()

            used_model_out = used_model

        else:

            response = self._parse_completion(completion.text)

            usage = completion.usage

            used_model_out = completion.model or used_model

        # Non-stream execute may soft-adjust confidence for invalid structured

        # payloads; Stage 1 Paper Chat streaming uses observe_answer instead.

        validation = self._validator.validate(response)

        if validation.ok and validation.response is not None:

            final = validation.response

        else:

            final = AIResponse(

                answer=response.answer or "Unable to produce a validated answer.",

                confidence="Low",

                evidence=list(response.evidence),

                limitations=list(response.limitations)

                + [f"validation: {e}" for e in validation.errors],

                workspace_refs=list(response.workspace_refs),

                metadata=dict(response.metadata),

            )

            validation = ValidationResult(

                ok=False,

                response=None,

                errors=list(validation.errors),

                warnings=list(validation.warnings),

            )

        return AIExecutionResult(

            response=final,

            usage=usage,

            latency_ms=latency_ms,

            model=used_model_out,

            prompt_version=prompt_ver,

            identity_version=identity_ver,

            context_schema_version=context_ver,

            validator=validation,

            metadata={

                "template_key": plan.template_key,

                "intent": plan.intent.value,

                "error": error,

                "entity_count": plan.metadata.get("entity_count"),

                "evidence_count": plan.metadata.get("evidence_count"),

                "file_id": plan.metadata.get("file_id"),

                "project_id": plan.metadata.get("project_id"),

            },

        )

    def stream_round(

        self,

        plan: PromptPlan,

        *,

        input_items: list[Any],

        tools: list[Any] | None = None,

        model: str | None = None,

        temperature: float | None = None,

        reasoning: dict[str, Any] | None = None,

        **kwargs: Any,

    ) -> Iterator[ResponsesStreamEvent]:

        """One Responses API round using ``plan.system_text`` as instructions.

        Plan is read-only. Does not rewrite streamed bytes. Tool-loop control

        stays in the route; call this once per model round.

        """

        used_model = model or self._default_model

        # Stage 1: instructions === legacy paper prompt only (not identity+skill).

        instructions = plan.system_text

        yield from self._stream_client.stream(

            model=used_model,

            instructions=instructions,

            input=input_items,

            tools=tools,

            temperature=temperature,

            reasoning=reasoning,

            **kwargs,

        )

    def observe_answer(

        self,

        plan: PromptPlan,

        answer_text: str,

        *,

        model: str,

        usage: TokenUsage | None = None,

        latency_ms: int = 0,

        rag_excerpt_count: int | None = None,

    ) -> AIExecutionResult:

        """Stage 1 validator policy: Observe → Record → Warn. Never rewrite."""

        prompt_ver = plan.prompt_version or prompt_version_for(plan.template_key)

        identity_ver = plan.identity_version or IDENTITY_VERSION

        context_ver = plan.context_schema_version or CONTEXT_SCHEMA_VERSION

        response = AIResponse(

            answer=answer_text or "",

            confidence="Medium",

            limitations=[],

        )

        validation = self._validator.validate(response)

        # Observe-only: keep the streamed answer bytes exactly as delivered.

        warnings = list(validation.warnings)

        if not validation.ok:

            warnings.extend(f"observe:{e}" for e in validation.errors)

        observed = ValidationResult(

            ok=validation.ok,

            response=None,

            errors=list(validation.errors),

            warnings=warnings,

        )

        plan_json = plan.to_json()

        plan_hash = hashlib.sha256(plan_json.encode("utf-8")).hexdigest()

        return AIExecutionResult(

            response=response,

            usage=usage or TokenUsage(),

            latency_ms=latency_ms,

            model=model,

            prompt_version=prompt_ver,

            identity_version=identity_ver,

            context_schema_version=context_ver,

            validator=observed,

            metadata={

                "template_key": plan.template_key,

                "intent": plan.intent.value,

                "file_id": plan.metadata.get("file_id"),

                "project_id": plan.metadata.get("project_id"),

                "rag_excerpt_count": rag_excerpt_count,

                "plan_hash": plan_hash,

                "identity_injected": plan.metadata.get("identity_injected", False),

                "observe_only": True,

            },

        )

    def _parse_completion(self, text: str) -> AIResponse:

        """Accept plain text or a JSON object matching AIResponse fields."""

        stripped = (text or "").strip()

        if stripped.startswith("{") and stripped.endswith("}"):

            try:

                data = json.loads(stripped)

                if isinstance(data, dict) and "answer" in data:

                    evidence = [

                        EvidenceReference(**e) if isinstance(e, dict) else e

                        for e in (data.get("evidence") or [])

                    ]

                    refs = [

                        WorkspaceReference(**r) if isinstance(r, dict) else r

                        for r in (data.get("workspace_refs") or [])

                    ]

                    return AIResponse(

                        answer=str(data.get("answer") or ""),

                        confidence=data.get("confidence") or "Medium",  # type: ignore[arg-type]

                        evidence=evidence,

                        limitations=list(data.get("limitations") or []),

                        workspace_refs=refs,

                        metadata=dict(data.get("metadata") or {}),

                    )

            except (json.JSONDecodeError, TypeError, ValueError):

                pass

        return AIResponse(

            answer=stripped,

            confidence="Medium",

            limitations=[],

        )
