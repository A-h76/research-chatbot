"""Shared job + outbox helpers used by multiple route stacks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def enqueue_upload_job_with_outbox(
    db,
    *,
    UploadJob: Any,
    OutboxEvent: Any,
    user_id: int,
    file_id: int,
    job_type: str,
    upload_batch_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    """Create UploadJob + paired job.enqueued outbox event (no commit)."""
    job = UploadJob(
        upload_batch_id=upload_batch_id,
        file_id=file_id,
        user_id=user_id,
        job_type=job_type,
        status="pending",
    )
    db.add(job)
    db.flush()
    event_payload = {"file_id": file_id}
    if payload:
        event_payload.update(payload)
    db.add(
        OutboxEvent(
            aggregate_type="upload_job",
            aggregate_id=job.id,
            event_type="job.enqueued",
            payload=json.dumps(event_payload, ensure_ascii=False),
        )
    )
    return job


def emit_contract_event(
    db,
    *,
    OutboxEvent: Any,
    aggregate_type: str,
    aggregate_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> Any:
    """Write contract-level event as already-dispatched outbox row."""
    event = OutboxEvent(
        aggregate_type=aggregate_type,
        aggregate_id=int(aggregate_id),
        event_type=event_type,
        payload=json.dumps(payload, ensure_ascii=False),
        status="dispatched",
        dispatched_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event
