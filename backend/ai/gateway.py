"""AI Gateway v1.0 — task/mode policy -> model resolution + telemetry.

This is infrastructure policy, not product feature logic:
feature code asks for (task, mode), never a raw model string.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

import yaml

from backend.ai.responses_adapter import OpenAIResponsesAdapter, ResponsesStreamEvent

log = logging.getLogger(__name__)

QUALITY_MODES = frozenset({"fast", "balanced", "publication"})

_REGISTRY_PATH = Path(__file__).parent.parent.parent / "docs" / "AI_MODEL_REGISTRY.yaml"


def validate_registry(openai_client=None, *, registry_path: Path | None = None) -> None:
    """Validate AI_MODEL_REGISTRY.yaml at startup.

    Logs a summary of each configured tier and model. If `openai_client` is
    provided, performs a lightweight models.retrieve() call per tier to confirm
    the model is accessible in the current API project. Raises RuntimeError on
    any inaccessible model so the application fails fast with a clear message.
    """
    path = registry_path or _REGISTRY_PATH
    if not path.exists():
        log.warning("AI_MODEL_REGISTRY.yaml not found at %s — skipping validation", path)
        return

    with open(path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    rv = registry.get("registry_version", "?")
    pv = registry.get("policy_version", "?")
    tiers = registry.get("tiers") or {}

    log.info("Loading AI_MODEL_REGISTRY.yaml (registry_version=%s policy_version=%s)...", rv, pv)

    failures: list[str] = []
    for tier_name, tier in tiers.items():
        provider = tier.get("provider", "openai")
        model = tier.get("model", "")
        if openai_client is not None and provider == "openai":
            try:
                openai_client.models.retrieve(model)
                log.info("  ✓ %-12s  %s  (%s)", tier_name, model, provider)
            except Exception as exc:
                log.error("  ✗ %-12s  %s  (%s) — %s", tier_name, model, provider, exc)
                failures.append(f"{tier_name}: {model} ({exc})")
        else:
            log.info("  ✓ %-12s  %s  (%s) [not verified]", tier_name, model, provider)

    if failures:
        raise RuntimeError(
            "AI Gateway startup validation failed — models not accessible in current API project:\n"
            + "\n".join(f"  • {f}" for f in failures)
        )

    log.info("Registry Version: %s | Policy Version: %s | AI Gateway Ready", rv, pv)


class AIGateway:
    def __init__(self, model_router, *, policy_path: str | None = None, openai_client: Any | None = None):
        self.model_router = model_router
        self.policy_path = policy_path or str(Path(__file__).with_name("policy.yaml"))
        self.policy = self._load_policy(self.policy_path)
        self._high_conf = float(os.environ.get("AI_GATEWAY_CONFIDENCE_HIGH", "0.95"))
        self._low_conf = float(os.environ.get("AI_GATEWAY_CONFIDENCE_LOW", "0.70"))
        self._responses: OpenAIResponsesAdapter | None = None
        if openai_client is not None:
            self.bind_responses_client(openai_client)

    def bind_responses_client(self, openai_client: Any) -> None:
        """Attach OpenAI Responses transport (stream + create) to this gateway."""
        self._responses = OpenAIResponsesAdapter(openai_client)

    @property
    def responses_adapter(self) -> OpenAIResponsesAdapter | None:
        return self._responses

    @staticmethod
    def _load_policy(path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        tasks = raw.get("tasks") or {}
        return {"tasks": tasks}

    def _normalize_mode(self, mode: str | None) -> str:
        m = (mode or "balanced").strip().lower()
        return m if m in QUALITY_MODES else "balanced"

    def _apply_confidence_routing(self, mode: str, confidence: float | None) -> str:
        if confidence is None:
            return mode
        if confidence < self._low_conf:
            return "publication"
        if confidence >= self._high_conf:
            return "fast"
        return mode

    def resolve_model(self, task: str, *, mode: str | None = None, confidence: float | None = None) -> str:
        base_mode = self._normalize_mode(mode)
        routed_mode = self._apply_confidence_routing(base_mode, confidence)
        task_policy = self.policy["tasks"].get(task) or {}
        model = task_policy.get(routed_mode) or task_policy.get("balanced")
        if model:
            return str(model)
        # Backward-compatible fallback to existing ModelRouter defaults/env.
        return self.model_router.get_model_for_task(task)

    def call(
        self,
        *,
        model_registry,
        task: str,
        messages: list[dict[str, Any]],
        mode: str | None = None,
        confidence: float | None = None,
        model: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute an LLM call.

        Prefer ``model`` from ``resolve_execution`` (Capability Router). When
        omitted, falls back to task/mode policy (migration shim).
        """
        chosen_mode = self._normalize_mode(mode)
        resolved_mode = self._apply_confidence_routing(chosen_mode, confidence)
        if model and str(model).strip():
            resolved_model = str(model).strip()
        else:
            resolved_model = self.resolve_model(task, mode=chosen_mode, confidence=confidence)
        started = time.perf_counter()
        success = False
        result: dict[str, Any] | None = None
        error_text = ""
        try:
            result = model_registry.call(resolved_model, messages, **kwargs)
            success = True
            return result
        except Exception as exc:
            error_text = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            tokens = int((result or {}).get("total_tokens") or 0)
            cost = float((result or {}).get("cost") or 0.0)
            log.info(
                "ai_gateway_call task=%s mode=%s resolved_mode=%s model=%s latency_ms=%s tokens=%s cost_usd=%s confidence=%s success=%s error=%s",
                task,
                chosen_mode,
                resolved_mode,
                resolved_model,
                latency_ms,
                tokens,
                cost,
                confidence if confidence is not None else "",
                success,
                error_text[:200] if error_text else "",
            )

    def stream_responses(
        self,
        *,
        model: str,
        instructions: str,
        input: list[Any],
        tools: list[Any] | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        task: str = "chat",
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> Iterator[ResponsesStreamEvent]:
        """Stream one Responses API round through the gateway-owned adapter."""
        if self._responses is None:
            raise RuntimeError("AIGateway responses client not bound — call bind_responses_client")
        tid = trace_id or str(uuid.uuid4())
        started = time.perf_counter()
        success = False
        error_text = ""
        try:
            yield from self._responses.stream(
                model=model,
                instructions=instructions,
                input=input,
                tools=tools,
                temperature=temperature,
                reasoning=reasoning,
                **kwargs,
            )
            success = True
        except Exception as exc:
            error_text = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            log.info(
                "ai_gateway_stream task=%s model=%s trace_id=%s latency_ms=%s success=%s error=%s",
                task,
                model,
                tid,
                latency_ms,
                success,
                error_text[:200] if error_text else "",
            )

    def create_responses(
        self,
        *,
        model: str,
        instructions: str,
        input: list[Any],
        tools: list[Any] | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        task: str = "chat",
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Non-streaming Responses API call through the gateway-owned adapter."""
        if self._responses is None:
            raise RuntimeError("AIGateway responses client not bound — call bind_responses_client")
        tid = trace_id or str(uuid.uuid4())
        started = time.perf_counter()
        success = False
        error_text = ""
        result: Any = None
        try:
            result = self._responses.create(
                model=model,
                instructions=instructions,
                input=input,
                tools=tools,
                temperature=temperature,
                reasoning=reasoning,
                **kwargs,
            )
            success = True
            return result
        except Exception as exc:
            error_text = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = getattr(result, "usage", None) if result is not None else None
            tin = getattr(usage, "input_tokens", None) if usage else None
            tout = getattr(usage, "output_tokens", None) if usage else None
            log.info(
                "ai_gateway_create task=%s model=%s trace_id=%s latency_ms=%s tokens_in=%s tokens_out=%s success=%s error=%s",
                task,
                model,
                tid,
                latency_ms,
                tin if tin is not None else "",
                tout if tout is not None else "",
                success,
                error_text[:200] if error_text else "",
            )
