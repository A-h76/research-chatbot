"""POST /api/uploads/bulk, GET /api/uploads/batch/<id>/status — the bulk
upload entry point `UploadBatch` was defined for but nothing wrote to:
"Nothing creates these yet — today's upload routes handle one file per
request — so this stays empty until a bulk-upload entry point exists"
(see UploadBatch's own docstring in server.py). This is that entry point.

Builds on the exact same primitives POST /api/documents/upload already
writes — UserFile, UploadJob, OutboxEvent, one file each per job — rather
than inventing a second upload pipeline: worker.py's HANDLERS pick up
each resulting UploadJob identically regardless of which route enqueued
it. No new "status" column on UserFile: UploadJob.status is already the
authoritative per-file processing state (pending|running|done|failed),
so batch progress is computed by aggregating each batch's UploadJob rows
rather than duplicating that state onto UserFile or onto UploadBatch
itself — one source of truth, no sync-drift risk.

Constructor-injected (SessionLocal, models, quota_service,
storage_backend), never `import server` — server.py runs as __main__, so
a module it reaches into importing "server" back re-executes the whole
file under a second module identity and recurses. Same pattern as every
other module in auth/, quotas/, and backend/ (see
backend/upload/routes.py's own docstring for the canonical explanation).
"""

import logging
import io
import os
import uuid

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from auth.decorators import jwt_required
from backend.jobs.outbox import enqueue_upload_job_with_outbox
from quotas.service import QuotaExceededError

from .validation import (
    DOCUMENT_EXTENSIONS,
    ValidationError,
    kind_for_extension,
    safe_filename,
    validate_upload_bytes,
)

log = logging.getLogger(__name__)

DEFAULT_MAX_BATCH_SIZE = 50
MAX_BATCH_SIZE = int(os.environ.get("MAX_BATCH_SIZE", str(DEFAULT_MAX_BATCH_SIZE)))


def create_bulk_upload_blueprint(
    *,
    SessionLocal,
    UserFile,
    UploadBatch,
    UploadJob,
    OutboxEvent,
    quota_service,
    storage_backend,
    limiter=None,
    import_spine=None,
    upload_service=None,
    Project=None,
):
    bp = Blueprint("bulk_upload", __name__, url_prefix="/api/uploads")

    def _upload_svc():
        if upload_service is not None:
            return upload_service
        from backend.upload.upload_service import UploadService

        return UploadService(
            UserFile,
            UploadBatch,
            import_spine=import_spine,
            UploadJob=UploadJob,
            OutboxEvent=OutboxEvent,
        )

    def _jwt_facade():
        from backend.upload.upload_service import JwtStorageFacade

        return JwtStorageFacade(storage_backend)

    def _limit(spec):
        def deco(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return deco

    @bp.route("/bulk", methods=["POST"])
    @jwt_required()
    @_limit("20 per hour")
    def upload_bulk():
        user_id = int(g.current_user)

        files = request.files.getlist("files[]") or request.files.getlist("files")
        if not files:
            return jsonify({"error": "no_files", "message": "No files provided"}), 400
        if len(files) > MAX_BATCH_SIZE:
            return (
                jsonify(
                    {
                        "error": "too_many_files",
                        "message": f"Maximum {MAX_BATCH_SIZE} files per batch",
                    }
                ),
                400,
            )

        # Validate every file up front so one bad file in the batch aborts
        # the whole request rather than partially uploading the rest.
        prepared = []
        total_bytes = 0
        for f in files:
            if not f or not f.filename:
                return jsonify({"error": "no_file", "message": "Empty file field in batch"}), 400
            try:
                data = f.read()
                ext, mime = validate_upload_bytes(
                    data, f.filename, allowed=DOCUMENT_EXTENSIONS
                )
            except ValidationError as e:
                log.warning(
                    "event=%s filename=%s message=%s",
                    e.code,
                    f.filename,
                    e.message,
                )
                return (
                    jsonify({"error": e.code, "message": f"{f.filename}: {e.message}"}),
                    400,
                )
            size = len(data)
            total_bytes += size
            prepared.append((data, ext, mime, size, f.filename))

        raw_project_id = request.form.get("project_id")
        project_id = None
        if raw_project_id not in (None, ""):
            if Project is None:
                return jsonify({"error": "validation", "message": "project_id not supported"}), 400
            from security.authz import resolve_owned_project_id

            db_pre = SessionLocal()
            try:
                project_id, denied = resolve_owned_project_id(
                    db_pre, Project, raw_project_id, user_id
                )
                if denied:
                    return jsonify({"error": "forbidden", "message": "project_not_found"}), 403
            finally:
                db_pre.close()

        try:
            quota_service.check_storage_quota(user_id, total_bytes)
        except QuotaExceededError as e:
            log.warning(
                "event=quota_exceeded kind=storage user_id=%s used=%s limit=%s",
                user_id,
                getattr(e, "used", ""),
                getattr(e, "limit", ""),
            )
            return (
                jsonify(
                    {
                        "error": "storage_quota_exceeded",
                        "message": f"Storage quota exceeded: {e.used + total_bytes} bytes "
                        f"would exceed the {e.limit} byte limit",
                    }
                ),
                403,
            )
        except ValueError:
            return jsonify({"error": "not_found", "message": "User not found"}), 404

        db = SessionLocal()
        uploaded_keys = []
        facade = _jwt_facade()
        svc = _upload_svc()
        try:
            batch = svc.ensure_batch(
                db,
                user_id,
                source="bulk_upload",
                file_count=len(prepared),
                project_id=project_id,
                increment=False,
            )

            jobs_out = []
            for data, ext, mime, size, original_name in prepared:
                filename = safe_filename(original_name, ext)
                key = facade.new_bulk_key(user_id, batch.id, filename)

                result = svc.store_jwt_bytes_and_register(
                    db,
                    facade,
                    user_id=user_id,
                    data=data,
                    filename=filename,
                    mime=mime,
                    kind=kind_for_extension(ext),
                    key=key,
                    project_id=project_id,
                    batch=batch,
                    batch_source="bulk_upload",
                    create_batch=False,
                )
                if not result.ok:
                    raise RuntimeError(result.error or "storage_unavailable")
                uploaded_keys.append(key)
                jobs_out.append(
                    {
                        "job_id": result.job_id,
                        "file_id": result.user_file.id,
                        "filename": filename,
                    }
                )

            db.commit()

            try:
                quota_service.increment_storage(user_id, total_bytes, delta_files=len(prepared))
            except Exception:
                pass

            return (
                jsonify(
                    {
                        "batch_id": batch.id,
                        "total_files": len(prepared),
                        "jobs": jobs_out,
                    }
                ),
                201,
            )
        except Exception:
            db.rollback()
            for key in uploaded_keys:
                try:
                    facade.delete(key)
                except Exception:
                    pass
            return (
                jsonify(
                    {
                        "error": "storage_unavailable",
                        "message": "Could not store the batch, try again",
                    }
                ),
                500,
            )
        finally:
            db.close()

    @bp.route("/batch/<int:batch_id>/status", methods=["GET"])
    @jwt_required()
    def batch_status(batch_id):
        user_id = int(g.current_user)
        db = SessionLocal()
        try:
            batch = db.get(UploadBatch, batch_id)
            if not batch or batch.user_id != user_id:
                return jsonify({"error": "not_found", "message": "Batch not found"}), 404

            # Intake only: one ``import`` job per uploaded file. Follow-ups
            # (phase1_analysis, paper_analysis, evidence_extract) must not
            # inflate progress — they used to share upload_batch_id and made
            # the UI show "2 of 1 file processed" with duplicate filenames.
            rows = db.execute(
                select(UploadJob, UserFile)
                .join(UserFile, UserFile.id == UploadJob.file_id)
                .where(
                    UploadJob.upload_batch_id == batch_id,
                    UploadJob.job_type == "import",
                )
            ).all()

            total = int(batch.file_count or 0) or len(rows)
            processed = sum(1 for job, _ in rows if job.status in ("done", "failed"))
            failed = sum(1 for job, _ in rows if job.status == "failed")
            if total == 0 or processed == 0:
                status = "pending"
            elif processed < total:
                status = "processing"
            else:
                status = "done"

            return (
                jsonify(
                    {
                        "batch_id": batch.id,
                        "total_files": total,
                        "processed_files": processed,
                        "failed_files": failed,
                        "status": status,
                        "jobs": [
                            {
                                "job_id": job.id,
                                "file_id": uf.id,
                                "filename": uf.name,
                                "status": job.status,
                                "error": getattr(job, "last_error", None),
                            }
                            for job, uf in rows
                        ],
                        "created_at": batch.created_at.isoformat() if batch.created_at else None,
                    }
                ),
                200,
            )
        finally:
            db.close()

    return bp
