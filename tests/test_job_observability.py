"""Unit + API tests for A-404 job observability."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server

from backend.jobs.observability import (
    classify_error_code,
    derive_lifecycle,
    job_status_cache_mapping,
    job_status_from_cache,
    serialize_job_status,
)


class _Job:
    def __init__(self, **kwargs):
        now = datetime.now(timezone.utc)
        self.id = kwargs.get("id", 1)
        self.user_id = kwargs.get("user_id", 1)
        self.file_id = kwargs.get("file_id", 9)
        self.job_type = kwargs.get("job_type", "evidence_extract")
        self.status = kwargs.get("status", "pending")
        self.attempts = kwargs.get("attempts", 0)
        self.last_error = kwargs.get("last_error")
        self.run_after = kwargs.get("run_after", now)
        self.created_at = kwargs.get("created_at", now - timedelta(seconds=5))
        self.started_at = kwargs.get("started_at")
        self.finished_at = kwargs.get("finished_at")
        self.updated_at = kwargs.get("updated_at", now)


def test_classify_error_codes():
    assert classify_error_code("missing_phase1") == "missing_phase1"
    assert classify_error_code("OpenAI timeout after 30s") == "provider_timeout"
    assert classify_error_code("unknown job_type: 'x'") == "unknown_job_type"


def test_lifecycle_retry_and_dead_letter():
    now = datetime.now(timezone.utc)
    assert (
        derive_lifecycle(status="pending", attempts=0, run_after=now - timedelta(seconds=1), now=now)
        == "queued"
    )
    assert (
        derive_lifecycle(status="pending", attempts=2, run_after=now + timedelta(seconds=60), now=now)
        == "retry_wait"
    )
    assert derive_lifecycle(status="failed", attempts=5, run_after=now, now=now) == "dead_letter"
    assert derive_lifecycle(status="done", attempts=0, run_after=now, now=now) == "succeeded"


def test_serialize_includes_retry_timings_error():
    now = datetime.now(timezone.utc)
    job = _Job(
        status="pending",
        attempts=2,
        last_error="provider timeout",
        run_after=now + timedelta(seconds=120),
        started_at=now - timedelta(seconds=3),
        finished_at=now - timedelta(seconds=1),
    )
    payload = serialize_job_status(job, max_attempts=5, cached=False, now=now)
    assert payload["status"] == "pending"
    assert payload["lifecycle"] == "retry_wait"
    assert payload["retry"]["will_retry"] is True
    assert payload["retry"]["backoff_seconds"] == 120
    assert payload["retry"]["max_attempts"] == 5
    assert payload["timings"]["duration_ms"] is not None
    assert payload["error"]["code"] == "provider_timeout"
    assert payload["error"]["retriable"] is True
    assert payload["last_error"] == "provider timeout"
    assert payload["file_id"] == 9


def test_cache_roundtrip_preserves_attempts_and_job_type():
    now = datetime.now(timezone.utc)
    job = _Job(status="failed", attempts=3, last_error="missing_phase1", finished_at=now)
    payload = serialize_job_status(job, max_attempts=5)
    mapping = job_status_cache_mapping(payload, user_id=42)
    assert mapping["attempts"] == "3"
    assert mapping["job_type"] == "evidence_extract"
    assert mapping["last_error"] == "missing_phase1"
    restored = job_status_from_cache(mapping, job_id=job.id)
    assert restored["cached"] is True
    assert restored["attempts"] == 3
    assert restored["job_type"] == "evidence_extract"
    assert restored["lifecycle"] == "dead_letter"
    assert restored["error"]["code"] == "missing_phase1"


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_job_status_api_observability_fields():
    db = server.SessionLocal()
    try:
        uid = 9101
        db.add(
            server.User(
                id=uid,
                email=f"obs{uid}@example.com",
                name=f"Obs {uid}",
                created_at=datetime.now(timezone.utc),
            )
        )
        now = datetime.now(timezone.utc)
        job = server.UploadJob(
            user_id=uid,
            file_id=None,
            job_type="evidence_extract",
            status="pending",
            attempts=1,
            last_error="OpenAI timeout",
            run_after=now + timedelta(seconds=60),
            started_at=now - timedelta(seconds=10),
            finished_at=now - timedelta(seconds=8),
            created_at=now - timedelta(seconds=20),
        )
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    client = _client()
    _login(client, uid)
    resp = client.get(f"/api/jobs/{job_id}/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["job_id"] == job_id
    assert body["status"] == "pending"
    assert body["job_type"] == "evidence_extract"
    assert body["attempts"] == 1
    assert body["last_error"] == "OpenAI timeout"
    assert body["lifecycle"] == "retry_wait"
    assert body["retry"]["will_retry"] is True
    assert body["timings"]["duration_ms"] is not None
    assert body["error"]["code"] == "provider_timeout"
    assert body["cached"] is False
