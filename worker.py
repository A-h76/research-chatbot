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
import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

import server
from server import (SessionLocal, UploadJob, OutboxEvent, UserFile,
                    extract_text, _process_document, _apply_metadata,
                    _run_paper_analysis, _enqueue_job, _sha256)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s worker: %(message)s")
log = logging.getLogger("worker")

POLL_INTERVAL_SECONDS = int(os.environ.get("WORKER_POLL_INTERVAL", "2"))
BATCH_SIZE = int(os.environ.get("WORKER_BATCH_SIZE", "10"))
MAX_ATTEMPTS = int(os.environ.get("WORKER_MAX_ATTEMPTS", "5"))


def _require_postgres():
    if not server.engine.dialect.name.startswith("postgres"):
        print(f"worker.py requires Postgres (FOR UPDATE SKIP LOCKED) — "
             f"DATABASE_URL currently resolves to a '{server.engine.dialect.name}' "
             f"engine. Point DATABASE_URL at Postgres/Neon to run this.")
        sys.exit(1)


def _get_text_for_file(uf):
    """Re-extract a file's text from storage. extract_metadata/paper_analysis
    jobs are dequeued independently of the import job that first extracted
    the text — there is no in-memory value to reuse across separate polls,
    possibly by a different worker process entirely."""
    ext = os.path.splitext(uf.name.lower())[1]
    with server.storage.storage_manager.provider.local_copy(uf.path, suffix=ext) as local_path:
        return extract_text(local_path, uf.mime, uf.name)


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
        _process_document(db, uf, local_path, uf.name, uf.mime,
                          job_id=job.id, on_processed=enqueue_followups)


def _handle_extract_metadata(db, job):
    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")
    text = _get_text_for_file(uf)
    content_hash = uf.content_hash or _sha256(text)
    _apply_metadata(job.file_id, text, content_hash, job_id=job.id)


def _handle_paper_analysis(db, job):
    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")
    text = _get_text_for_file(uf)
    content_hash = uf.content_hash or _sha256(text)
    _run_paper_analysis(job.file_id, text, content_hash, job_id=job.id)


HANDLERS = {
    "import": _handle_import,
    "extract_metadata": _handle_extract_metadata,
    "paper_analysis": _handle_paper_analysis,
}


# --------------------------------------------------------------- outbox / cache
def _mark_outbox_dispatched(db, job_id):
    events = db.execute(
        select(OutboxEvent).where(OutboxEvent.aggregate_type == "upload_job",
                                  OutboxEvent.aggregate_id == job_id,
                                  OutboxEvent.status == "pending")
    ).scalars().all()
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
        jobs = db.execute(
            select(UploadJob)
            .where(UploadJob.status == "pending", UploadJob.run_after <= func.now())
            .order_by(UploadJob.created_at)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).scalars().all()

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
            log.warning("job %s not in 'running' state (%s) — skipping",
                       job_id, job.status)
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
            db.rollback()   # discard any partial work from this attempt
            job = db.get(UploadJob, job_id)   # re-fetch: rollback expired it
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
                log.error("job %s (%s) failed permanently after %d attempts: %s",
                         job.id, job.job_type, job.attempts, exc)
            else:
                # Back to 'pending' for the next poll to pick up again —
                # not before run_after, which backs off linearly per
                # attempt (60s, 120s, 180s, ...). No outbox update here:
                # the job isn't actually finished yet, just paused.
                job.status = "pending"
                job.run_after = datetime.now(timezone.utc) + timedelta(seconds=job.attempts * 60)
                log.warning("job %s (%s) failed (attempt %d/%d), retrying at %s: %s",
                           job.id, job.job_type, job.attempts, MAX_ATTEMPTS,
                           job.run_after.isoformat(), exc)
            db.commit()
            _sync_status_cache(job)
    finally:
        db.close()


def main():
    _require_postgres()
    log.info("worker starting — poll every %ss, batch size %s, max attempts %s",
             POLL_INTERVAL_SECONDS, BATCH_SIZE, MAX_ATTEMPTS)
    while True:
        try:
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
