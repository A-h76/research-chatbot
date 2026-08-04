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
from backend.ai import AIGateway, ModelRegistry, PromptRegistry
from observability import configure_logging, correlation_id_var, record_upload_job_outcome, start_worker_metrics_server
from server import (
    AnalysisPipelineResult,
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
# Loopback by default so the worker scrape port is not world-reachable (PR2).
METRICS_BIND = (os.environ.get("WORKER_METRICS_BIND") or "127.0.0.1").strip() or "127.0.0.1"
DEFAULT_AI_MODE = (os.environ.get("AI_QUALITY_MODE") or "balanced").strip().lower()

ai_gateway = AIGateway(server.model_router)


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
    PAPER_ANALYSIS_RESPONSE_FORMAT,
    ensure_default_prompts,
    medical_response_format,
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
            # Extract DOI → Crossref enrich BEFORE Phase 1 so AI analysis
            # benefits from verified title/authors/abstract. Soft-fail.
            try:
                from backend.scholarly.crossref import enrich_from_extracted_text
                enrich_from_extracted_text(db, file_id, text or "")
            except Exception as _cx_exc:
                import logging as _log
                _log.getLogger(__name__).warning(
                    "crossref pre-phase1 skipped file_id=%s: %s", file_id, _cx_exc
                )
            # Phase 1 pipeline is the primary structured analysis path.
            # paper_analysis (LLM overview) runs after phase1 so PromptBuilder
            # can consume persisted Phase 1 outputs.
            _enqueue_job(db, uf.user_id, file_id, "phase1_analysis", job.upload_batch_id)

        _process_document(
            db,
            uf,
            local_path,
            uf.name,
            uf.mime,
            job_id=job.id,
            on_processed=enqueue_followups,
        )




def _handle_phase1_analysis(db, job):
    """Run Phase 1.1–1.7 via AnalysisPipelineService, persist results, apply
    bibliographic metadata, then enqueue LLM paper_analysis as a consumer."""
    from backend.analysis_pipeline.models import AnalysisOptions
    from backend.analysis_pipeline.persistence import apply_metadata_to_user_file, save_analysis_result
    from backend.analysis_pipeline.service import AnalysisPipelineService, extract_bibliographic_fields

    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")

    # Idempotency: reuse completed row for same content_hash
    existing = db.execute(
        select(AnalysisPipelineResult).where(AnalysisPipelineResult.file_id == job.file_id)
    ).scalar_one_or_none()
    if (
        existing
        and existing.status == "done"
        and uf.content_hash
        and existing.content_hash == uf.content_hash
    ):
        _enqueue_job(db, uf.user_id, job.file_id, "paper_analysis", job.upload_batch_id)
        try:
            from backend.evidence.services.auto_extract import maybe_enqueue_evidence_extract

            maybe_enqueue_evidence_extract(
                db,
                user_id=uf.user_id,
                file_id=job.file_id,
                UserFile=UserFile,
                UploadJob=UploadJob,
                OutboxEvent=OutboxEvent,
                upload_batch_id=job.upload_batch_id,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("auto evidence_extract enqueue skipped: %s", exc)
        db.commit()
        return

    if existing is None:
        existing = AnalysisPipelineResult(file_id=job.file_id, user_id=uf.user_id, status="running")
        db.add(existing)
    else:
        existing.status = "running"
        existing.error = ""
    db.commit()

    ext = os.path.splitext(uf.name.lower())[1]
    try:
        with server.storage.storage_manager.provider.local_copy(uf.path, suffix=ext) as local_path:
            result = AnalysisPipelineService().analyze_file_path(
                local_path,
                file_id=job.file_id,
                options=AnalysisOptions(),
                document_id=str(job.file_id),
            )
        save_analysis_result(db, AnalysisPipelineResult, result, user_id=uf.user_id)
        uf = db.get(UserFile, job.file_id)
        if not uf:
            raise RuntimeError(f"file {job.file_id} no longer exists")
        fields = extract_bibliographic_fields(result.phase_results)
        apply_metadata_to_user_file(uf, fields, only_empty=True)
        if result.content_hash:
            uf.content_hash = result.content_hash
        if fields:
            uf.meta_status = "done"
        db.commit()
        if result.status.value == "failed":
            raise RuntimeError("; ".join(result.errors) or "phase1_analysis failed")

        # Crossref already ran in import→enqueue_followups (before Phase 1).
        # Phase 1.1 may still fill empty bibliographic fields via only_empty=True.
        _enqueue_job(db, uf.user_id, job.file_id, "paper_analysis", job.upload_batch_id)
        # Paper Analysis 2.4 — auto evidence happy path (existing job family).
        try:
            from backend.evidence.services.auto_extract import maybe_enqueue_evidence_extract

            maybe_enqueue_evidence_extract(
                db,
                user_id=uf.user_id,
                file_id=job.file_id,
                UserFile=UserFile,
                UploadJob=UploadJob,
                OutboxEvent=OutboxEvent,
                upload_batch_id=job.upload_batch_id,
            )
        except Exception as exc:  # noqa: BLE001 — never fail phase1 on auto extract
            log.warning("auto evidence_extract enqueue skipped: %s", exc)
        db.commit()
    except Exception as exc:
        db.rollback()
        row = db.execute(
            select(AnalysisPipelineResult).where(AnalysisPipelineResult.file_id == job.file_id)
        ).scalar_one_or_none()
        if row:
            row.status = "failed"
            row.error = str(exc)[:500]
            db.commit()
        raise


def _handle_extract_metadata(db, job):
    """DEPRECATED drain shim (#17): no LLM — redirect leftover queue rows.

    Historical ``extract_metadata`` jobs may still sit ``pending`` after the
    cutover to ``import → phase1_analysis → paper_analysis``. Completing them
    as a no-op LLM path and enqueueing ``phase1_analysis`` empties the queue
    without a one-shot SQL migrate. New uploads never enqueue this type.
    """
    from backend.analysis_pipeline.deprecation import warn_legacy

    warn_legacy("worker._handle_extract_metadata")
    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")

    # Already satisfied by Phase 1.1 or a prior legacy run — nothing to do.
    if uf.meta_status == "done":
        return

    # Redirect metadata + Phase 1 engines onto the canonical chain.
    _enqueue_job(db, uf.user_id, job.file_id, "phase1_analysis", job.upload_batch_id)


def _handle_paper_analysis(db, job):
    """LLM paper overview — consumes Phase 1 outputs when available."""
    from backend.analysis_pipeline.persistence import load_analysis_result
    from backend.analysis_pipeline.summary import build_phase1_prompt_context, classification_domain_hint

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
        phase1 = load_analysis_result(db, AnalysisPipelineResult, job.file_id)
        phase1_context = build_phase1_prompt_context(phase1.phase_results) if phase1 else ""
        domain_hint = classification_domain_hint(phase1.phase_results if phase1 else None)

        prompt_registry = PromptRegistry(db)
        model_registry = ModelRegistry(db)
        # Prefer PromptBuilder when Phase 1 context exists so structured
        # analysis is in the Retrieved Context section; fall back to registry.
        if phase1_context:
            builder = server.get_prompt_builder(db)
            assembled = builder.build(
                "Analyze this paper",
                "paper_analysis",
                project_id=uf.project_id,
                user_id=uf.user_id,
                rag_context=text[:ANALYSIS_MAX_CHARS],
                domain=domain_hint,
                metadata={
                    "title": uf.title or "",
                    "authors": uf.authors or "",
                    "year": uf.year or "",
                    "venue": uf.venue or "",
                },
                phase1_context=phase1_context,
            )
            prompt_text = assembled.final
            response_format = PAPER_ANALYSIS_RESPONSE_FORMAT
            if assembled.domain == "medical":
                response_format = medical_response_format(assembled.document_type)
            result = ai_gateway.call(
                model_registry=model_registry,
                task="paper_analysis",
                mode=DEFAULT_AI_MODE,
                messages=[{"role": "user", "content": prompt_text}],
                user_id=uf.user_id,
                response_format=response_format,
            )
        else:
            prompt, _prompt_version = prompt_registry.get_prompt(
                "paper_analysis",
                variables={"text": text[:ANALYSIS_MAX_CHARS], "max_chars": ANALYSIS_MAX_CHARS},
            )
            result = ai_gateway.call(
                model_registry=model_registry,
                task="paper_analysis",
                mode=DEFAULT_AI_MODE,
                messages=[{"role": "user", "content": prompt}],
                user_id=uf.user_id,
                response_format=PAPER_ANALYSIS_RESPONSE_FORMAT,
            )
        data = json.loads(result["content"])

        for field in ANALYSIS_ARRAY_FIELDS:
            v = data.get(field)
            if isinstance(v, str):
                data[field] = [v] if v else []
            elif not isinstance(v, list):
                data[field] = []
        if not isinstance(data.get("important_terms"), list):
            data["important_terms"] = []

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


def _handle_evidence_extract(db, job):
    """Project Phase 1 outputs into candidate EvidenceObjects (Week 2)."""
    from backend.analysis_pipeline.persistence import load_analysis_result
    from backend.evidence.services.extract_service import run_evidence_extraction

    # Prefer project_id from outbox payload; fall back to file.project_id
    project_id = None
    force = False
    already_applied = False
    events = (
        db.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_type == "upload_job",
                OutboxEvent.aggregate_id == job.id,
            )
        )
        .scalars()
        .all()
    )
    for ev in events:
        try:
            payload = json.loads(ev.payload or "{}")
        except json.JSONDecodeError:
            payload = {}
        if payload.get("project_id") is not None:
            project_id = int(payload["project_id"])
        force = bool(payload.get("force")) or force
        already_applied = bool(payload.get("already_applied")) or already_applied

    if already_applied and not force:
        return

    uf = db.get(UserFile, job.file_id)
    if not uf:
        raise RuntimeError(f"file {job.file_id} no longer exists")
    if project_id is None:
        if uf.project_id is None:
            raise RuntimeError("evidence_extract requires project_id")
        project_id = int(uf.project_id)

    run_evidence_extraction(
        db,
        user_id=job.user_id,
        project_id=project_id,
        file_id=job.file_id,
        UserFile=UserFile,
        AnalysisPipelineResult=AnalysisPipelineResult,
        EvidenceObject=server.EvidenceObject,
        EvidenceExtractionRun=server.EvidenceExtractionRun,
        load_analysis_result=load_analysis_result,
        force=force,
        job_id=job.id,
        OutboxEvent=OutboxEvent,
    )


def _research_job_payload(db, job) -> dict:
    events = (
        db.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_type == "upload_job",
                OutboxEvent.aggregate_id == job.id,
            )
        )
        .scalars()
        .all()
    )
    for ev in events:
        try:
            payload = json.loads(ev.payload or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and (
            payload.get("type") in ("literature_review", "theme_map")
            or payload.get("project_id") is not None
        ):
            return payload
    return {}


def _handle_theme_map(db, job):
    """W6 — async theme map over project evidence."""
    from backend.research.jobs import run_theme_map_job, store_research_job_result

    payload = _research_job_payload(db, job)
    project_id = payload.get("project_id")
    if project_id is None:
        raise RuntimeError("theme_map requires project_id in outbox payload")
    file_ids = payload.get("file_ids")
    result = run_theme_map_job(
        db,
        user_id=job.user_id,
        project_id=int(project_id),
        EvidenceObject=server.EvidenceObject,
        select=select,
        file_ids=[int(x) for x in file_ids] if file_ids else None,
    )
    store_research_job_result(
        db,
        OutboxEvent=OutboxEvent,
        job_id=job.id,
        kind="theme_map",
        result=result,
    )


def _handle_literature_review(db, job):
    """W6 — async grounded literature review (Writing Intelligence)."""
    from backend.evidence.services.permission_service import require_owned_document
    from backend.research.jobs import run_literature_review_job, store_research_job_result

    payload = _research_job_payload(db, job)
    query = payload.get("query")
    if not isinstance(query, dict):
        raise RuntimeError("literature_review requires query in outbox payload")
    result = run_literature_review_job(
        db,
        user_id=job.user_id,
        query=query,
        EvidenceObject=server.EvidenceObject,
        WritingSentenceBinding=server.WritingSentenceBinding,
        WritingDocument=server.WritingDocument,
        ReviewerRun=server.ReviewerRun,
        ReviewerFinding=server.ReviewerFinding,
        select=select,
        require_owned_document=require_owned_document,
        composer=None,
    )
    store_research_job_result(
        db,
        OutboxEvent=OutboxEvent,
        job_id=job.id,
        kind="literature_review",
        result=result,
    )


def _handle_library_sync(db, job):
    """Phase 1b — worker-backed Zotero/Mendeley incremental metadata sync."""
    from backend.library.sync_job import run_library_sync_job

    run_library_sync_job(
        db,
        job,
        OutboxEvent=OutboxEvent,
        select_fn=select,
        SessionLocal=SessionLocal,
        LibraryConnection=server.LibraryConnection,
        LibrarySyncRun=server.LibrarySyncRun,
        UserFile=UserFile,
        Project=server.Project,
        enrich_file_from_doi=getattr(server, "_enrich_file_from_doi", None),
        secret_key=server.app.secret_key or "",
    )


HANDLERS = {
    "import": _handle_import,
    "extract_metadata": _handle_extract_metadata,
    "phase1_analysis": _handle_phase1_analysis,
    "paper_analysis": _handle_paper_analysis,
    "evidence_extract": _handle_evidence_extract,
    "theme_map": _handle_theme_map,
    "literature_review": _handle_literature_review,
    "library_sync": _handle_library_sync,
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
    unconditionally at every status transition.

    A-404: write the full observability payload so cache hits retain
    job_type / attempts / last_error / retry / timings.
    """
    try:
        server._cache_upload_job_status(job)
    except AttributeError:
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
            _record_job_metrics(job, outcome="done")
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
            _record_job_metrics(
                job, outcome="failed" if job.status == "failed" else "retry"
            )
    finally:
        db.close()


def _record_job_metrics(job, *, outcome: str) -> None:
    duration = None
    if job.started_at and job.finished_at:
        try:
            start = job.started_at
            end = job.finished_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            duration = max(0.0, (end - start).total_seconds())
        except Exception:
            duration = None
    try:
        record_upload_job_outcome(
            job_type=job.job_type or "unknown",
            outcome=outcome,
            duration_seconds=duration if outcome in {"done", "failed"} else None,
        )
    except Exception:
        log.warning("job metrics record failed", exc_info=True)


def _heartbeat():
    """Upserts the single worker_heartbeats row (id=1) — see
    GET /api/worker/health in server.py, the only consumer. Best-effort:
    a failed heartbeat write shouldn't take down the poll loop itself.

    Also runs scholarly provider cache/metrics cleanup at most once per day
    (DB-locked so multiple workers don't all run it).
    """
    db = SessionLocal()
    try:
        hb = db.get(WorkerHeartbeat, 1)
        now = datetime.now(timezone.utc)
        if hb is None:
            db.add(WorkerHeartbeat(id=1, last_seen_at=now))
        else:
            hb.last_seen_at = now
        db.commit()
        try:
            from backend.scholarly import try_daily_cleanup
            try_daily_cleanup(db)
        except Exception:
            log.debug("provider daily cleanup skipped", exc_info=True)
    except Exception:
        log.exception("heartbeat write failed")
        db.rollback()
    finally:
        db.close()


def main():
    _require_postgres()
    _ensure_prompts()
    start_worker_metrics_server(METRICS_PORT, addr=METRICS_BIND)
    log.info(
        "worker starting — poll every %ss, batch size %s, max attempts %s, " "metrics on %s:%s",
        POLL_INTERVAL_SECONDS,
        BATCH_SIZE,
        MAX_ATTEMPTS,
        METRICS_BIND,
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
