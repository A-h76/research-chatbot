"""Direct-upload + job-status routes extracted from server.py.

A-302 File Processing: POST /api/files and GET /api/jobs/<id>/status.
Behavior is intentionally preserved; this module only moves route boundaries.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

from flask import Blueprint, jsonify, request, session


def create_processing_upload_blueprint(
    *,
    SessionLocal,
    Project,
    User,
    UserFile,
    UploadBatch,
    UploadJob,
    OutboxEvent,
    StorageUsage,
    ALLOWED_EXTENSIONS,
    MAX_FILE_MB,
    upload_dir,
    storage,
    login_required,
    limiter,
    resolve_owned_project_id,
    log_security_event,
    find_duplicate_file,
    file_to_dict,
    validate_extension,
    UploadValidationError,
    validate_upload_path,
    kind_for_extension,
    adjust_storage_usage,
    get_job_status_cache,
    set_job_status_cache,
    default_storage_limit_bytes,
):
    bp = Blueprint("processing_upload_routes", __name__)

    @bp.route("/api/files", methods=["POST"])
    @login_required
    @limiter.limit("60 per hour")
    def upload_file():
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "no_file"}), 400
        name = f.filename
        try:
            ext = validate_extension(name, allowed=ALLOWED_EXTENSIONS)
        except UploadValidationError as e:
            log_security_event("invalid_mime", code=e.code, filename=name, message=e.message)
            return jsonify({"error": e.code, "detail": e.message}), 400

        conversation_id = request.form.get("conversation_id", type=int)
        project_id = request.form.get("project_id", type=int)
        batch_id = request.form.get("batch_id", type=int)
        disk_name = uuid.uuid4().hex + ext
        path = os.path.join(upload_dir, disk_name)
        f.save(path)
        size = os.path.getsize(path)
        try:
            _, mime = validate_upload_path(
                path,
                name,
                allowed=ALLOWED_EXTENSIONS,
                size_bytes=size,
                max_mb=MAX_FILE_MB,
            )
        except UploadValidationError as e:
            event = "virus_detected" if e.code == "virus_detected" else "invalid_mime"
            log_security_event(event, code=e.code, filename=name, message=e.message)
            try:
                os.remove(path)
            except OSError:
                pass
            return jsonify({"error": e.code, "detail": e.message}), 400

        kind = kind_for_extension(ext)

        checksum = storage.sha256_file(path)
        uid = session["user_id"]

        db = SessionLocal()
        try:
            project_id, project_denied = resolve_owned_project_id(db, Project, project_id, uid)
            if project_denied:
                log_security_event(
                    "authz_denied",
                    resource="project",
                    action="upload",
                    user_id=uid,
                    project_id=request.form.get("project_id"),
                )
            dup = find_duplicate_file(db, uid, checksum)
            if dup:
                result = file_to_dict(dup)
                result["note"] = None
                result["duplicate"] = True
                return jsonify(result)

            try:
                storage.upload(disk_name, path)
            except Exception:
                logging.exception("storage upload failed for %s", disk_name)
                return jsonify({"error": "storage_unavailable"}), 502

            batch = db.get(UploadBatch, batch_id) if batch_id else None
            if not batch or batch.user_id != uid:
                batch = UploadBatch(
                    user_id=uid,
                    project_id=project_id,
                    conversation_id=conversation_id,
                    source="library",
                    file_count=0,
                )
                db.add(batch)
                db.flush()
            batch.file_count = (batch.file_count or 0) + 1

            usage = db.get(StorageUsage, uid)
            already_used = usage.bytes_used if usage else 0
            user_row = db.get(User, uid)
            limit_bytes = (user_row.storage_limit_bytes if user_row else None) or default_storage_limit_bytes
            if already_used + size > limit_bytes:
                db.rollback()
                try:
                    os.remove(path)
                except OSError:
                    pass
                return (
                    jsonify(
                        {
                            "error": "storage_quota_exceeded",
                            "detail": f"Storage limit is {limit_bytes // (1024 * 1024)} MB",
                        }
                    ),
                    403,
                )

            uf = UserFile(
                user_id=uid,
                project_id=project_id,
                conversation_id=conversation_id,
                name=name[:300],
                mime=mime,
                kind=kind,
                path=disk_name,
                size=size,
                checksum_sha256=checksum,
            )
            db.add(uf)
            db.flush()

            job_id = None
            if kind == "document":
                job = UploadJob(
                    upload_batch_id=batch.id,
                    file_id=uf.id,
                    user_id=uid,
                    job_type="import",
                    status="pending",
                )
                db.add(job)
                db.flush()
                job_id = job.id

                db.add(
                    OutboxEvent(
                        aggregate_type="upload_job",
                        aggregate_id=job.id,
                        event_type="job.enqueued",
                        payload=json.dumps({"file_id": uf.id}),
                    )
                )

            adjust_storage_usage(db, uid, delta_bytes=size, delta_files=1)

            db.commit()

            result = file_to_dict(uf)
            result["note"] = None
            result["job_id"] = job_id
            return jsonify(result)
        finally:
            db.close()
            try:
                os.remove(path)
            except OSError:
                pass

    @bp.route("/api/jobs/<int:job_id>/status")
    @login_required
    def job_status(job_id):
        from backend.jobs.observability import (
            DEFAULT_MAX_ATTEMPTS,
            job_status_from_cache,
            serialize_job_status,
        )

        cached = get_job_status_cache(job_id)
        if cached:
            if int(cached.get("user_id", 0)) != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            payload = job_status_from_cache(cached, job_id=job_id)
            if payload is not None:
                return jsonify(payload)

        db = SessionLocal()
        try:
            job = db.get(UploadJob, job_id)
            if not job or job.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            payload = serialize_job_status(
                job, max_attempts=DEFAULT_MAX_ATTEMPTS, cached=False
            )
            set_job_status_cache(job)
            return jsonify(payload)
        finally:
            db.close()

    return bp
