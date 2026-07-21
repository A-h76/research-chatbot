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

import json
import os
import uuid

from flask import Blueprint, request, jsonify, g
from sqlalchemy import select

from auth.decorators import jwt_required
from quotas.service import QuotaExceededError

from .validation import (
    validate_extension,
    validate_size,
    safe_filename,
    ValidationError,
)

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
):
    bp = Blueprint("bulk_upload", __name__, url_prefix="/api/uploads")

    @bp.route("/bulk", methods=["POST"])
    @jwt_required()
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
                ext = validate_extension(f.filename)
                f.stream.seek(0, 2)  # SEEK_END — size without touching disk
                size = f.stream.tell()
                f.stream.seek(0)
                validate_size(size)
            except ValidationError as e:
                return (
                    jsonify({"error": e.code, "message": f"{f.filename}: {e.message}"}),
                    400,
                )
            total_bytes += size
            prepared.append((f, ext, size))

        try:
            quota_service.check_storage_quota(user_id, total_bytes)
        except QuotaExceededError as e:
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
        try:
            batch = UploadBatch(user_id=user_id, source="bulk_upload", file_count=len(prepared))
            db.add(batch)
            db.flush()  # assigns batch.id

            jobs_out = []
            for f, ext, size in prepared:
                filename = safe_filename(f.filename, ext)
                key = f"users/{user_id}/uploads/{batch.id}/{uuid.uuid4().hex}/{filename}"

                storage_backend.upload(f.stream, key, content_type=f.mimetype)
                uploaded_keys.append(key)

                uf = UserFile(
                    user_id=user_id,
                    name=filename[:300],
                    mime=f.mimetype,
                    kind="document",
                    path=key,
                    size=size,
                )
                db.add(uf)
                db.flush()  # assigns uf.id

                job = UploadJob(
                    upload_batch_id=batch.id,
                    file_id=uf.id,
                    user_id=user_id,
                    job_type="import",
                    status="pending",
                )
                db.add(job)
                db.flush()  # assigns job.id

                db.add(
                    OutboxEvent(
                        aggregate_type="upload_job",
                        aggregate_id=job.id,
                        event_type="job.enqueued",
                        payload=json.dumps({"file_id": uf.id}),
                    )
                )
                jobs_out.append({"job_id": job.id, "file_id": uf.id, "filename": filename})

            db.commit()

            # Best-effort, same as /api/documents/upload: the batch is
            # already safely stored and recorded, so a quota-log hiccup
            # here shouldn't undo it, only get logged.
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
                    storage_backend.delete(key)
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

            rows = db.execute(
                select(UploadJob, UserFile)
                .join(UserFile, UserFile.id == UploadJob.file_id)
                .where(UploadJob.upload_batch_id == batch_id)
            ).all()

            total = len(rows)
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
                        "total_files": batch.file_count,
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
