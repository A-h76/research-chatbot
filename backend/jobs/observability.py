"""Job observability helpers (A-404).

Derive lifecycle / retry / timings / error diagnostics from UploadJob rows
without changing the core status enum (pending|running|done|failed).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

DEFAULT_MAX_ATTEMPTS = int(os.environ.get("WORKER_MAX_ATTEMPTS", "5"))

# Order matters — first match wins.
_ERROR_CODE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("not_research_ready", re.compile(r"not_research_ready|not research ready", re.I)),
    ("missing_phase1", re.compile(r"missing_phase1|missing phase.?1", re.I)),
    ("provider_timeout", re.compile(r"timeout|timed out|deadline exceeded", re.I)),
    ("rate_limited", re.compile(r"rate.?limit|429|too many requests", re.I)),
    ("auth_failed", re.compile(r"unauthorized|forbidden|401|403|invalid.?api.?key", re.I)),
    ("not_found", re.compile(r"\bnot found\b|404|no such", re.I)),
    ("validation_error", re.compile(r"validation|invalid|unsupported", re.I)),
    ("unknown_job_type", re.compile(r"unknown job_type", re.I)),
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return None


def _as_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            text = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _ms_between(start: Any, end: Any) -> int | None:
    a = _as_dt(start)
    b = _as_dt(end)
    if a is None or b is None:
        return None
    return max(0, int((b - a).total_seconds() * 1000))


def classify_error_code(message: str | None) -> str | None:
    """Best-effort stable error code from free-text last_error."""
    if not message:
        return None
    for code, pattern in _ERROR_CODE_PATTERNS:
        if pattern.search(message):
            return code
    return "handler_error"


def derive_lifecycle(
    *,
    status: str,
    attempts: int,
    run_after: Any,
    now: datetime | None = None,
) -> str:
    """Additive structured state — does not replace `status`."""
    st = (status or "").strip().lower()
    if st == "done":
        return "succeeded"
    if st == "failed":
        return "dead_letter"
    if st == "running":
        return "running"
    if st == "pending":
        if attempts > 0:
            return "retry_wait"
        due = _as_dt(run_after)
        clock = now or datetime.now(timezone.utc)
        if due is not None and due > clock:
            return "scheduled"
        return "queued"
    return st or "unknown"


def classify_error(
    message: str | None,
    *,
    status: str,
    attempts: int,
    max_attempts: int,
) -> dict[str, Any] | None:
    if not message:
        return None
    code = classify_error_code(message)
    permanent_codes = {
        "not_research_ready",
        "missing_phase1",
        "validation_error",
        "unknown_job_type",
    }
    if status == "failed":
        retriable = False
    elif status == "pending" and attempts > 0 and attempts < max_attempts:
        retriable = True
    else:
        retriable = code not in permanent_codes
    return {
        "message": message,
        "code": code,
        "retriable": bool(retriable),
    }


def build_retry_metadata(
    *,
    status: str,
    attempts: int,
    max_attempts: int,
    run_after: Any,
) -> dict[str, Any]:
    attempts = int(attempts or 0)
    max_attempts = int(max_attempts or DEFAULT_MAX_ATTEMPTS)
    backoff_seconds = attempts * 60 if attempts > 0 and status == "pending" else None
    will_retry = status == "pending" and attempts > 0 and attempts < max_attempts
    return {
        "attempts": attempts,
        "max_attempts": max_attempts,
        "run_after": _iso(run_after),
        "backoff_seconds": backoff_seconds,
        "will_retry": will_retry,
    }


def build_timings(
    *,
    created_at: Any,
    started_at: Any,
    finished_at: Any,
    updated_at: Any,
    status: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    duration_ms = _ms_between(started_at, finished_at)
    if duration_ms is None and status == "running" and started_at is not None:
        duration_ms = _ms_between(started_at, clock)
    queue_wait_ms = _ms_between(created_at, started_at)
    return {
        "created_at": _iso(created_at),
        "started_at": _iso(started_at),
        "finished_at": _iso(finished_at),
        "updated_at": _iso(updated_at),
        "duration_ms": duration_ms,
        "queue_wait_ms": queue_wait_ms,
    }


def serialize_job_status(
    job: Any,
    *,
    max_attempts: int | None = None,
    cached: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Public GET /api/jobs/<id>/status body (additive under A-404)."""
    max_attempts = int(max_attempts or DEFAULT_MAX_ATTEMPTS)
    status = str(getattr(job, "status", None) or "pending")
    attempts = int(getattr(job, "attempts", 0) or 0)
    last_error = getattr(job, "last_error", None) or None
    progress = 100 if status == "done" else 0
    updated_at = getattr(job, "updated_at", None)
    run_after = getattr(job, "run_after", None)
    created_at = getattr(job, "created_at", None)
    started_at = getattr(job, "started_at", None)
    finished_at = getattr(job, "finished_at", None)
    file_id = getattr(job, "file_id", None)
    job_type = getattr(job, "job_type", None)
    job_id = int(getattr(job, "id"))

    lifecycle = derive_lifecycle(
        status=status, attempts=attempts, run_after=run_after, now=now
    )
    retry = build_retry_metadata(
        status=status,
        attempts=attempts,
        max_attempts=max_attempts,
        run_after=run_after,
    )
    timings = build_timings(
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        updated_at=updated_at,
        status=status,
        now=now,
    )
    error = classify_error(
        last_error, status=status, attempts=attempts, max_attempts=max_attempts
    )

    return {
        # Frozen-ish existing keys (do not remove)
        "job_id": job_id,
        "status": status,
        "job_type": job_type,
        "attempts": attempts,
        "last_error": last_error,
        "progress": progress,
        "updated_at": _iso(updated_at),
        "cached": bool(cached),
        # Additive A-404
        "lifecycle": lifecycle,
        "retry": retry,
        "timings": timings,
        "error": error,
        "file_id": file_id,
        "max_attempts": max_attempts,
    }


def job_status_cache_mapping(payload: dict[str, Any], *, user_id: int) -> dict[str, str]:
    """Flatten status payload for Redis hash (all string values)."""
    return {
        "user_id": str(int(user_id)),
        "status": str(payload.get("status") or ""),
        "progress": str(int(payload.get("progress") or 0)),
        "updated_at": str(payload.get("updated_at") or ""),
        "job_type": str(payload.get("job_type") or ""),
        "attempts": str(int(payload.get("attempts") or 0)),
        "last_error": str(payload.get("last_error") or ""),
        "payload_json": json.dumps(payload, ensure_ascii=False, default=str),
    }


def job_status_from_cache(cached: dict[str, Any], *, job_id: int) -> dict[str, Any] | None:
    """Rebuild public status from Redis hash; prefer payload_json when present."""
    raw = cached.get("payload_json")
    if raw:
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                payload = dict(payload)
                payload["job_id"] = int(job_id)
                payload["cached"] = True
                return payload
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    # Legacy / partial cache — best effort
    if not cached.get("status"):
        return None
    return {
        "job_id": int(job_id),
        "status": cached.get("status"),
        "job_type": cached.get("job_type") or None,
        "attempts": int(cached.get("attempts") or 0),
        "last_error": cached.get("last_error") or None,
        "progress": int(cached.get("progress") or 0),
        "updated_at": cached.get("updated_at") or None,
        "cached": True,
    }
