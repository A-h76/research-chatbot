"""Utility LLM + embedding — ACR + Gateway + AI Ledger (Bite 8)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from backend.ai.capability_router.types import ExecutionPlan


def invoke_prompt_llm(
    *,
    ai_gateway: Any,
    model_registry: Any,
    prompt: str,
    plan: ExecutionPlan,
    prompt_version: str,
    path: str,
    task: str,
    user_id: int | None = None,
    json_mode: bool = False,
    quality_mode: str | None = None,
    extra: dict[str, Any] | None = None,
    cost_action: str = "chat",
    ai_gate: Any | None = None,
    estimated_cost: float | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Single-user-prompt utility call under Capability Router provenance."""
    from backend.ai.ai_ledger import AILedgerEntry, hash_output
    from backend.ai.ledger_facade import record_acr_execution

    trace_id = str(uuid.uuid4())
    started = time.perf_counter()
    messages = [{"role": "user", "content": prompt}]
    call_kwargs: dict[str, Any] = {
        "model_registry": model_registry,
        "task": task,
        "mode": quality_mode or "balanced",
        "model": plan.model,
        "messages": messages,
    }
    if user_id is not None:
        call_kwargs["user_id"] = user_id
    if json_mode:
        call_kwargs["response_format"] = {"type": "json_object"}

    result = ai_gateway.call(**call_kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)

    content = (result or {}).get("content") or ""
    tin = (result or {}).get("prompt_tokens")
    tout = (result or {}).get("completion_tokens")
    tokens = int((result or {}).get("total_tokens") or 0) or None
    cost = float((result or {}).get("cost") or 0.0)

    ledger_extra = {"path": path}
    if extra:
        ledger_extra.update(extra)
    if user_id is not None:
        ledger_extra["user_id"] = user_id

    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version=prompt_version,
        tokens_in=int(tin) if tin is not None else None,
        tokens_out=int(tout) if tout is not None else tokens,
        cost_usd=cost if cost else None,
        latency_ms=latency_ms,
        output_hash=hash_output(content) if content else None,
        trace_id=trace_id,
        status="completed",
        extra=ledger_extra,
    )
    record_acr_execution(
        entry,
        model_registry=model_registry,
        user_id=user_id,
        cost_action=cost_action,
        ai_gate=ai_gate,
        estimated_cost=estimated_cost,
    )

    provenance = plan.to_provenance(
        tokens=tokens,
        cost_usd=cost if cost else None,
        duration_ms=latency_ms,
        prompt_version=prompt_version,
        execution_id=entry.execution_id,
    ).to_dict()
    return content, provenance


def invoke_embed_texts(
    *,
    model_registry: Any,
    texts: list[str],
    user_id: int | None = None,
    path: str = "embed",
) -> list[list[float] | None]:
    """Batch embeddings with AI Ledger provenance (keyword fallback callers use None slots)."""
    from backend.ai.ai_ledger import AILedgerEntry
    from backend.ai.ledger_facade import record_acr_execution
    from backend.ai.capability_router.utility_resolve import (
        PROMPT_VERSION_EMBED,
        resolve_embed_execution,
    )

    if not texts:
        return []

    plan = resolve_embed_execution()
    out: list[list[float] | None] = []
    total_tokens = 0
    embed_model = getattr(model_registry, "embed_model", None) or "text-embedding-3-small"

    try:
        for text in texts:
            try:
                vector = model_registry.embed(text, user_id=user_id, skip_cost_ledger=True)
                out.append(vector)
                total_tokens += int(getattr(model_registry, "_last_embed_tokens", 0) or 0)
            except Exception:
                out.append(None)
        entry = AILedgerEntry.from_plan(
            plan,
            prompt_version=PROMPT_VERSION_EMBED,
            tokens_in=total_tokens,
            tokens_out=0,
            trace_id=str(uuid.uuid4()),
            status="completed",
            extra={
                "path": path,
                "user_id": user_id,
                "batch_size": len(texts),
                "embed_model": embed_model,
            },
        )
        record_acr_execution(
            entry,
            model_registry=model_registry,
            user_id=user_id,
            cost_action="embedding",
        )
        return out
    except Exception:
        return [None] * len(texts)


def invoke_query_embedding(
    *,
    model_registry: Any,
    text: str,
    user_id: int,
    path: str,
) -> list[float]:
    """Single-query embed for search/RAG retrieval (ACR + AI Ledger).

    Raises ``ModelError`` when embedding fails — JWT routes require strict 502.
    """
    from backend.ai import ModelError

    vectors = invoke_embed_texts(
        model_registry=model_registry,
        texts=[text],
        user_id=user_id,
        path=path,
    )
    if not vectors or vectors[0] is None:
        embed_model = getattr(model_registry, "embed_model", None) or "text-embedding-3-small"
        raise ModelError("embedding failed", provider="openai", model=embed_model)
    return vectors[0]


def make_embed_texts_fn(
    *,
    get_model_registry: Callable[[Any], Any],
    SessionLocal: Callable[[], Any],
    path: str = "embed",
) -> Callable[[list[str], int | None], list[list[float] | None]]:
    """Factory matching legacy ``embed_texts(texts, user_id=None)`` signature."""

    def _embed(texts: list[str], user_id: int | None = None) -> list[list[float] | None]:
        db = SessionLocal()
        try:
            registry = get_model_registry(db)
            return invoke_embed_texts(
                model_registry=registry,
                texts=texts,
                user_id=user_id,
                path=path,
            )
        finally:
            db.close()

    return _embed
