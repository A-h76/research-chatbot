"""AI Ledger — first-class record of every platform AI execution (ADR-0016 v1.0).

In-memory + optional DB persistence later. Feature code should call
``record_execution`` after gateway / router-resolved calls; artifacts embed a
compact summary via ``ExecutionPlan.to_provenance``.

---------------------------------------------------------------------------
Ledger write path (Bite 11)
---------------------------------------------------------------------------
Platform ACR flows call ``record_platform_execution`` / ``record_acr_execution``
(``backend.ai.ledger_facade``). CostLedger rows are **projections** of AI Ledger
entries — ModelRegistry skips DB cost writes when ``skip_cost_ledger=True`` (Gateway default).
Legacy ``responses_text`` / direct ``ModelRegistry.call`` without the façade may still
log cost at the registry until those paths retire.
---------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.ai.capability_router.types import ExecutionPlan

logger = logging.getLogger(__name__)

LEDGER_VERSION = "1.0"

_lock = threading.Lock()
_ENTRIES: list[dict[str, Any]] = []
_MAX_MEMORY = 2000


@dataclass
class AILedgerEntry:
    execution_id: str
    research_job: str
    capability: str
    execution_profile: dict[str, Any]
    execution_policy: str
    provider: str
    model: str
    prompt_version: str = ""
    tools_used: list[str] = field(default_factory=list)
    evidence_source_ids: list[str] = field(default_factory=list)
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    output_hash: str | None = None
    evaluation: dict[str, Any] | None = None
    trace_id: str = ""
    parent_execution_id: str | None = None
    status: str = "completed"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    router_version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_plan(
        cls,
        plan: ExecutionPlan,
        *,
        prompt_version: str = "",
        tools_used: list[str] | None = None,
        evidence_source_ids: list[str] | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        output_hash: str | None = None,
        evaluation: dict[str, Any] | None = None,
        execution_id: str | None = None,
        trace_id: str = "",
        parent_execution_id: str | None = None,
        status: str = "completed",
        extra: dict[str, Any] | None = None,
    ) -> AILedgerEntry:
        return cls(
            execution_id=execution_id or str(uuid.uuid4()),
            research_job=plan.research_job.value,
            capability=plan.capability.value,
            execution_profile=plan.execution_profile.to_dict(),
            execution_policy=plan.execution_policy.value,
            provider=plan.provider.value,
            model=plan.model,
            prompt_version=prompt_version or plan.prompt_name or "",
            tools_used=list(tools_used or []),
            evidence_source_ids=list(evidence_source_ids or []),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            output_hash=output_hash,
            evaluation=evaluation,
            trace_id=trace_id or str(uuid.uuid4()),
            parent_execution_id=parent_execution_id,
            status=status,
            router_version=plan.router_version,
            extra=dict(extra or {}),
        )


def hash_output(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def record_execution(entry: AILedgerEntry | dict[str, Any]) -> dict[str, Any]:
    """Append to the in-process ledger. Soft-fails; never raises to callers."""
    try:
        payload = entry.to_dict() if isinstance(entry, AILedgerEntry) else dict(entry)
        with _lock:
            _ENTRIES.append(payload)
            if len(_ENTRIES) > _MAX_MEMORY:
                del _ENTRIES[: len(_ENTRIES) - _MAX_MEMORY]
        return payload
    except Exception as exc:
        logger.debug("ai_ledger record soft-fail: %s", exc)
        return {}


def recent_executions(*, limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        return list(_ENTRIES[-max(1, min(limit, 500)) :])


def clear_ledger_for_tests() -> None:
    with _lock:
        _ENTRIES.clear()
