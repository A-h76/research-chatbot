"""Unified AI execution write façade (Evolution Tracker · Bite 11).

AI Ledger is the system of record for platform executions; CostLedger rows are
**projections** derived from the same entry (tokens, model, user) — not a second
independent write path from ModelRegistry during ACR flows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from observability import record_ai_call

from backend.ai.ai_ledger import AILedgerEntry, record_execution

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CostProjection:
    """Financial + quota projection for one AI Ledger entry."""

    db_session: Any
    cost_ledger: Any
    user_id: int | None
    action: str  # chat | embedding | research | analysis
    prompt_version_id: int | None = None
    estimated_cost: float | None = None
    ai_gate: Any | None = None
    operation: str | None = None  # ai_gate operation; defaults to action


def _entry_dict(entry: AILedgerEntry | dict[str, Any]) -> dict[str, Any]:
    return entry.to_dict() if isinstance(entry, AILedgerEntry) else dict(entry)


def project_cost_from_entry(
    entry: AILedgerEntry | dict[str, Any],
    projection: CostProjection,
) -> float:
    """Write one CostLedger row from ledger entry token fields. Returns cost USD."""
    payload = _entry_dict(entry)
    model = str(payload.get("model") or "")
    tin = int(payload.get("tokens_in") or 0)
    tout = int(payload.get("tokens_out") or 0)
    total = tin + tout
    cost = payload.get("cost_usd")
    if cost is None:
        cost = projection.cost_ledger.estimate_cost(model, tin, tout)
    else:
        cost = float(cost)

    if projection.user_id is not None:
        try:
            projection.cost_ledger.log(
                projection.db_session,
                user_id=projection.user_id,
                model=model,
                prompt_tokens=tin,
                completion_tokens=tout,
                total_tokens=total,
                cost=cost,
                action=projection.action,
                prompt_version_id=projection.prompt_version_id,
                estimated_cost=projection.estimated_cost,
            )
        except Exception:
            logger.warning("ledger_facade cost projection failed", exc_info=True)

    if projection.ai_gate is not None and projection.user_id is not None:
        try:
            projection.ai_gate.record_usage(
                projection.user_id,
                tokens=total,
                cost_usd=cost,
                operation=projection.operation or projection.action,
            )
        except Exception:
            logger.warning("ledger_facade quota projection failed", exc_info=True)

    return float(cost)


def record_platform_execution(
    entry: AILedgerEntry | dict[str, Any],
    *,
    cost_projection: CostProjection | None = None,
) -> dict[str, Any]:
    """Single write façade: AI Ledger (+ optional CostLedger / quota projection)."""
    payload = record_execution(entry)
    if payload:
        _emit_ai_execution_completed(payload, entry=entry)
    if not payload or cost_projection is None:
        return payload

    model = str(payload.get("model") or "")
    tin = int(payload.get("tokens_in") or 0)
    tout = int(payload.get("tokens_out") or 0)
    if model:
        record_ai_call(model, prompt_tokens=tin, completion_tokens=tout)

    cost = project_cost_from_entry(entry, cost_projection)
    if payload.get("cost_usd") is None and cost:
        payload["cost_usd"] = cost
    return payload


def _emit_ai_execution_completed(
    payload: dict[str, Any],
    *,
    entry: AILedgerEntry | dict[str, Any],
) -> None:
    """Domain event after a successful AI Ledger write (Bite 14)."""
    execution_id = payload.get("execution_id") or getattr(entry, "execution_id", None)
    if not execution_id and isinstance(entry, dict):
        execution_id = entry.get("execution_id")
    if not execution_id:
        return
    status = str(payload.get("status") or "completed")
    if status not in ("completed", "ok", "success"):
        return
    try:
        from backend.domain_events import ai_execution_completed, publish

        extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
        if not extra and isinstance(entry, dict):
            extra = entry.get("extra") if isinstance(entry.get("extra"), dict) else {}
        elif not extra:
            extra = getattr(entry, "extra", None) or {}
        user_id = extra.get("user_id") if isinstance(extra, dict) else None
        publish(
            ai_execution_completed(
                execution_id=str(execution_id),
                user_id=int(user_id) if user_id is not None else None,
                model=str(payload.get("model") or ""),
                status=status,
                task=str(
                    payload.get("research_job")
                    or payload.get("capability")
                    or payload.get("task")
                    or ""
                ),
                correlation_id=str(payload.get("trace_id") or "") or None,
            )
        )
    except Exception:
        logger.warning("AIExecutionCompleted domain event failed", exc_info=True)


def record_acr_execution(
    entry: AILedgerEntry,
    *,
    model_registry: Any,
    user_id: int | None,
    cost_action: str = "chat",
    prompt_version_id: int | None = None,
    ai_gate: Any | None = None,
    estimated_cost: float | None = None,
) -> dict[str, Any]:
    """ACR engine helper — project cost when registry has a DB session."""
    projection = None
    db_session = getattr(model_registry, "db_session", None)
    cost_ledger = getattr(model_registry, "_cost_ledger", None)
    if user_id is not None and db_session is not None and cost_ledger is not None:
        projection = CostProjection(
            db_session=db_session,
            cost_ledger=cost_ledger,
            user_id=user_id,
            action=cost_action,
            prompt_version_id=prompt_version_id,
            ai_gate=ai_gate,
            estimated_cost=estimated_cost,
        )
    return record_platform_execution(entry, cost_projection=projection)
