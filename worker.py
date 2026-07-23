"""Queue Worker — polls upload_jobs, claims work with FOR UPDATE SKIP
LOCKED, executes it, and marks the paired outbox event dispatched.
Replaces the threading.Thread(daemon=True) calls upload_file() and
_process_document() used to make: a job survives a worker crash between
attempts (it's a committed row, not a thread), and two workers can run
side by side without double-processing the same job.

Run with: python worker.py

Requires Postgres — FOR UPDATE SKIP LOCKED is not supported by the
SQLite dev fallback, and this process refuses to start against it.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

import server

# ModelRegistry/PromptRegistry constructed directly (constructor-injection,
# same pattern as auth/quotas/backend — see §3 of brain.md), not reached
# into via any server.py-side instance: server.py doesn't hold module-level
# singletons for either (get_prompt_registry()/get_model_registry() there
# are themselves request-scoped factories, not something to import and
# reuse). worker.py already does `import server` for the DB models/engine
# above — safe here since worker.py is its own standalone process, never
# imported back by server.py itself.
from backend.ai import ModelRegistry, PromptRegistry
from observability import configure_logging, correlation_id_var, start_worker_metrics_server
from server import (
    OutboxEvent,
    PaperAnalysis,
    SessionLocal,
    UploadJob,
    UserFile,
    WorkerHeartbeat,
    _enqueue_job,
    _process_document,
    _sha256,
    extract_text,
)

configure_logging()
log = logging.getLogger("worker")

POLL_INTERVAL_SECONDS = int(os.environ.get("WORKER_POLL_INTERVAL", "2"))
BATCH_SIZE = int(os.environ.get("WORKER_BATCH_SIZE", "10"))
MAX_ATTEMPTS = int(os.environ.get("WORKER_MAX_ATTEMPTS", "5"))
METRICS_PORT = int(os.environ.get("WORKER_METRICS_PORT", "9101"))


def _require_postgres():
    if not server.engine.dialect.name.startswith("postgres"):
        print(
            f"worker.py requires Postgres (FOR UPDATE SKIP LOCKED) — "
            f"DATABASE_URL currently resolves to a '{server.engine.dialect.name}' "
            f"engine. Point DATABASE_URL at Postgres/Neon to run this."
        )
        sys.exit(1)


def _get_text_for_file(uf):
    """Re-extract a file's text from storage. extract_metadata/paper_analysis
    jobs are dequeued independently of the import job that first extracted
    the text — there is no in-memory value to reuse across separate polls,
    possibly by a different worker process entirely."""
    ext = os.path.splitext(uf.name.lower())[1]
    with server.storage.storage_manager.provider.local_copy(uf.path, suffix=ext) as local_path:
        return extract_text(local_path, uf.mime, uf.name)


# --------------------------------------------------------------- AI layer prompts
# Prompt content/constants live in backend/ai/prompts.py, not here — it's
# shared with server.py's POST /api/documents/<id>/analysis, which does
# the same conceptual operation synchronously instead of via the queue.
# worker.py can't be imported by server.py (see that module's own
# docstring for why), so a neutral third module is where both meet.
from backend.ai.prompts import (
    ANALYSIS_ARRAY_FIELDS,
    ANALYSIS_MAX_CHARS,
    META_EXCERPT_CHARS,
    ensure_default_prompts,
)


def _ensure_prompts():
    db = SessionLocal()
    try:
        ensure_default_prompts(db)
    finally:
        db.close()


# --------------------------------------------------------------- job handlers
def _handle_import(db, job):
    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")
    ext = os.path.splitext(uf.name.lower())[1]
    with server.storage.storage_manager.provider.local_copy(uf.path, suffix=ext) as local_path:

        def enqueue_followups(file_id, text, content_hash):
            # Replaces _process_document's old extract_metadata()/
            # trigger_paper_analysis() thread spawns — same follow-on
            # stages, enqueued transactionally instead.
            _enqueue_job(db, uf.user_id, file_id, "extract_metadata", job.upload_batch_id)
            _enqueue_job(db, uf.user_id, file_id, "paper_analysis", job.upload_batch_id)

        _process_document(
            db,
            uf,
            local_path,
            uf.name,
            uf.mime,
            job_id=job.id,
            on_processed=enqueue_followups,
        )


_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _handle_extract_metadata(db, job):
    """Root cause: kept the exact idempotency/field-validation semantics
    server.py's _apply_metadata already had (content_hash short-circuit,
    4-digit year regex, per-field length caps) — only the AI backend
    changed, from responses_text()/Responses API to ModelRegistry/Chat
    Completions. job lifecycle (status/attempts/retry) is entirely
    run_job()'s job; this function's only contract is "do the work, or
    raise" — no _start_upload_job/_finish_upload_job bookkeeping needed,
    unlike the legacy thread-spawned callers _apply_metadata still serves."""
    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")

    text = _get_text_for_file(uf)
    content_hash = uf.content_hash or _sha256(text)
    if uf.content_hash == content_hash and uf.meta_status == "done":
        return

    uf.meta_status = "running"
    db.commit()

    try:
        prompt_registry = PromptRegistry(db)
        model_registry = ModelRegistry(db)
        prompt, _prompt_version = prompt_registry.get_prompt(
            "extract_metadata",
            variables={"excerpt": text[:META_EXCERPT_CHARS], "max_chars": META_EXCERPT_CHARS},
        )
        result = model_registry.call(
            server.UTILITY_MODEL,
            [{"role": "user", "content": prompt}],
            user_id=uf.user_id,
            response_format={"type": "json_object"},
        )
        data = json.loads(result["content"])

        uf = db.get(UserFile, job.file_id)  # re-fetch: another writer may have touched it
        if not uf:
            return
        uf.content_hash = content_hash
        uf.meta_status = "done"
        title = data.get("title")
        if title:
            uf.title = str(title)[:500]
        authors = data.get("authors")
        if authors:
            uf.authors = str(authors)[:1000]
        year = data.get("year")
        if year:
            m = _YEAR_RE.search(str(year))
            if m:
                uf.year = m.group(0)
        venue = data.get("venue")
        if venue:
            uf.venue = str(venue)[:300]
        doi = data.get("doi")
        if doi:
            uf.doi = str(doi)[:200]
        abstract = data.get("abstract")
        if abstract:
            uf.abstract = str(abstract)[:8000]
        db.commit()
    except Exception:
        db.rollback()
        uf = db.get(UserFile, job.file_id)
        if uf:
            uf.meta_status = "failed"
            db.commit()
        raise  # let run_job()'s own try/except apply retry/backoff


def _handle_paper_analysis(db, job):
    """Same relationship to server.py's _run_paper_analysis as
    _handle_extract_metadata has to _apply_metadata above — idempotency
    and field-normalization behavior preserved, AI backend swapped."""
    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")

    text = _get_text_for_file(uf)
    content_hash = uf.content_hash or _sha256(text)

    pa = db.execute(select(PaperAnalysis).where(PaperAnalysis.file_id == job.file_id)).scalar_one_or_none()
    if pa is None:
        pa = PaperAnalysis(file_id=job.file_id, user_id=uf.user_id)
        db.add(pa)
        db.commit()

    if pa.content_hash == content_hash and pa.status == "done":
        return

    pa.status = "running"
    pa.error = ""
    db.commit()

    try:
        prompt_registry = PromptRegistry(db)
        model_registry = ModelRegistry(db)
        prompt, _prompt_version = prompt_registry.get_prompt(
            "paper_analysis",
            variables={"text": text[:ANALYSIS_MAX_CHARS], "max_chars": ANALYSIS_MAX_CHARS},
        )
        result = model_registry.call(
            server.UTILITY_MODEL,
            [{"role": "user", "content": prompt}],
            user_id=uf.user_id,
            response_format={"type": "json_object"},
        )
        data = json.loads(result["content"])

        for field in ANALYSIS_ARRAY_FIELDS:
            v = data.get(field)
            if isinstance(v, str):
                data[field] = [v] if v else []
            elif not isinstance(v, list):
                data[field] = []
        if not isinstance(data.get("important_terms"), dict):
            data["important_terms"] = {}

        pa = db.execute(select(PaperAnalysis).where(PaperAnalysis.file_id == job.file_id)).scalar_one_or_none()
        if pa is None:
            return
        pa.status = "done"
        pa.content_hash = content_hash
        pa.model = server.UTILITY_MODEL
        pa.data = json.dumps(data, ensure_ascii=False)
        pa.error = ""
        db.commit()
    except Exception as exc:
        db.rollback()
        pa = db.execute(select(PaperAnalysis).where(PaperAnalysis.file_id == job.file_id)).scalar_one_or_none()
        if pa:
            pa.status = "failed"
            pa.error = str(exc)[:500]
            db.commit()
        raise  # let run_job()'s own try/except apply retry/backoff


HANDLERS = {
    "import": _handle_import,
    "extract_metadata": _handle_extract_metadata,
    "paper_analysis": _handle_paper_analysis,
}


# --------------------------------------------------------------- outbox / cache
def _mark_outbox_dispatched(db, job_id):
    events = (
        db.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_type == "upload_job",
                OutboxEvent.aggregate_id == job_id,
                OutboxEvent.status == "pending",
            )
        )
        .scalars()
        .all()
    )
    for ev in events:
        ev.status = "dispatched"
        ev.dispatched_at = datetime.now(timezone.utc)


def _sync_status_cache(job):
    """Push the job's current status to Redis (database-design.md §5's
    job:{id}:status key, 1h TTL) — server._set_job_status_cache() is a
    no-op if Redis isn't configured/reachable, so this is safe to call
    unconditionally at every status transition."""
    progress = 100 if job.status == "done" else 0
    server._set_job_status_cache(job.id, job.status, progress, job.updated_at, job.user_id)


# --------------------------------------------------------------- poll loop
def claim_batch():
    """One FOR UPDATE SKIP LOCKED pass: claim up to BATCH_SIZE pending, due
    jobs and mark them 'running'. The lock only needs to stop two workers
    claiming the same row in the same instant — once committed as
    'running', the WHERE status='pending' clause alone keeps every other
    worker off it, lock or no lock."""
    db = SessionLocal()
    try:
        jobs = (
            db.execute(
                select(UploadJob)
                .where(UploadJob.status == "pending", UploadJob.run_after <= func.now())
                .order_by(UploadJob.created_at)
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )

        claimed = []
        now = datetime.now(timezone.utc)
        for job in jobs:
            job.status = "running"
            job.started_at = now
            claimed.append(job.id)
        db.commit()
        for job in jobs:
            _sync_status_cache(job)
        return claimed
    finally:
        db.close()


def run_job(job_id):
    # One job = one correlation id, same idea as one HTTP request = one id
    # in server.py — every log line this job's handler emits carries it.
    correlation_id_var.set(f"job-{job_id}")
    db = SessionLocal()
    try:
        job = db.get(UploadJob, job_id)
        if not job:
            return
        if job.status != "running":
            # Only claim_batch() should ever hand run_job() a job id, and
            # only right after marking it 'running' — a job that's already
            # terminal (done/failed) or still 'pending' getting here means
            # something upstream double-dispatched it. Refuse rather than
            # silently reprocess.
            log.warning("job %s not in 'running' state (%s) — skipping", job_id, job.status)
            return
        try:
            handler = HANDLERS.get(job.job_type)
            if handler is None:
                raise ValueError(f"unknown job_type: {job.job_type!r}")
            handler(db, job)

            job.status = "done"
            job.finished_at = datetime.now(timezone.utc)
            _mark_outbox_dispatched(db, job.id)
            db.commit()
            _sync_status_cache(job)
            log.info("job %s (%s) done", job.id, job.job_type)

        except Exception as exc:
            db.rollback()  # discard any partial work from this attempt
            job = db.get(UploadJob, job_id)  # re-fetch: rollback expired it
            job.attempts = (job.attempts or 0) + 1
            job.last_error = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            if job.attempts >= MAX_ATTEMPTS:
                # Retries exhausted — this row IS the dead-letter queue
                # (processing-pipeline-architecture.md §7): status stays
                # 'failed'; a human requeues it (status='pending',
                # attempts=0) once the underlying cause is fixed.
                job.status = "failed"
                _mark_outbox_dispatched(db, job.id)
                log.error(
                    "job %s (%s) failed permanently after %d attempts: %s",
                    job.id,
                    job.job_type,
                    job.attempts,
                    exc,
                )
            else:
                # Back to 'pending' for the next poll to pick up again —
                # not before run_after, which backs off linearly per
                # attempt (60s, 120s, 180s, ...). No outbox update here:
                # the job isn't actually finished yet, just paused.
                job.status = "pending"
                job.run_after = datetime.now(timezone.utc) + timedelta(seconds=job.attempts * 60)
                log.warning(
                    "job %s (%s) failed (attempt %d/%d), retrying at %s: %s",
                    job.id,
                    job.job_type,
                    job.attempts,
                    MAX_ATTEMPTS,
                    job.run_after.isoformat(),
                    exc,
                )
            db.commit()
            _sync_status_cache(job)
    finally:
        db.close()


def _heartbeat():
    """Upserts the single worker_heartbeats row (id=1) — see
    GET /api/worker/health in server.py, the only consumer. Best-effort:
    a failed heartbeat write shouldn't take down the poll loop itself."""
    db = SessionLocal()
    try:
        hb = db.get(WorkerHeartbeat, 1)
        now = datetime.now(timezone.utc)
        if hb is None:
            db.add(WorkerHeartbeat(id=1, last_seen_at=now))
        else:
            hb.last_seen_at = now
        db.commit()
    except Exception:
        log.exception("heartbeat write failed")
        db.rollback()
    finally:
        db.close()


def main():
    _require_postgres()
    _ensure_prompts()
    start_worker_metrics_server(METRICS_PORT)
    log.info(
        "worker starting — poll every %ss, batch size %s, max attempts %s, " "metrics on :%s",
        POLL_INTERVAL_SECONDS,
        BATCH_SIZE,
        MAX_ATTEMPTS,
        METRICS_PORT,
    )
    while True:
        try:
            _heartbeat()
            claimed = claim_batch()
            for job_id in claimed:
                run_job(job_id)
            if not claimed:
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            log.info("worker stopping")
            break
        except Exception:
            log.exception("poll loop error — backing off")
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
