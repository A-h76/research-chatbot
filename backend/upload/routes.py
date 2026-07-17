"""POST /api/documents/upload — a new, Bearer-JWT-authenticated upload
entry point for API clients, alongside the existing session-based
POST /api/files (same relationship as magic-link auth to Google OAuth:
an additional flow, not a replacement — see auth/magic_link.py).

Deliberately reuses the app's existing upload infrastructure rather than
building a parallel one:
  - UserFile (the `files` table) is the file record — no new Document
    model/table. The response still uses the "document_id" key the spec
    asked for; it's just UserFile.id underneath.
  - UploadJob + OutboxEvent, the same transactional-outbox pair
    POST /api/files writes, so the existing queue worker actually picks
    this file up — "processing started" in the response is true.
  - QuotaService (quotas/service.py) for the storage-quota check/record —
    built in an earlier task but never wired into an upload path until
    now.
  - backend.storage's StorageBackend for the object write — this route
    is that abstraction's first real caller.

Constructor-injected (SessionLocal, models, quota_service, storage_backend)
rather than `import server`: server.py runs as __main__, so a module it
reaches into importing "server" back re-executes the whole file under a
second module identity and recurses. Same pattern as every module in
auth/ and quotas/.
"""

import json
import logging
import uuid

from flask import Blueprint, request, jsonify, g

from auth.decorators import jwt_required
from quotas.service import QuotaExceededError

from .validation import (
    validate_extension,
    validate_size,
    safe_filename,
    ValidationError,
)


def create_documents_blueprint(
    *,
    SessionLocal,
    UserFile,
    UploadBatch,
    UploadJob,
    OutboxEvent,
    quota_service,
    storage_backend,
):
    bp = Blueprint("documents", __name__, url_prefix="/api/documents")
    log = logging.getLogger(__name__)

    @bp.route("/upload", methods=["POST"])
    @jwt_required()
    def upload_document():
        user_id = int(g.current_user)

        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "no_file", "message": "No file provided"}), 400

        try:
            ext = validate_extension(f.filename)
        except ValidationError as e:
            return jsonify({"error": e.code, "message": e.message}), 400

        f.stream.seek(0, 2)  # SEEK_END — size without touching disk
        size = f.stream.tell()
        f.stream.seek(0)

        try:
            validate_size(size)
        except ValidationError as e:
            return jsonify({"error": e.code, "message": e.message}), 400

        try:
            quota_service.check_storage_quota(user_id, size)
        except QuotaExceededError as e:
            return (
                jsonify(
                    {
                        "error": "storage_quota_exceeded",
                        "message": f"Storage quota exceeded: {e.used + size} bytes "
                        f"would exceed the {e.limit} byte limit",
                    }
                ),
                403,
            )
        except ValueError:
            return jsonify({"error": "not_found", "message": "User not found"}), 404

        filename = safe_filename(f.filename, ext)
        key = f"users/{user_id}/documents/{uuid.uuid4().hex}/{filename}"

        try:
            storage_backend.upload(f.stream, key, content_type=f.mimetype)
        except Exception:
            return (
                jsonify(
                    {
                        "error": "storage_unavailable",
                        "message": "Could not store the file, try again",
                    }
                ),
                502,
            )

        db = SessionLocal()
        try:
            batch = UploadBatch(user_id=user_id, source="api_documents", file_count=1)
            db.add(batch)
            db.flush()  # assigns batch.id

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

            db.commit()

            # QuotaService owns its own session/transaction (see
            # quotas/service.py) — it can't be folded into the commit
            # above, so it runs after that commit succeeds rather than
            # before. Best-effort like the app's existing AI-usage
            # logging: the file is already safely stored and recorded,
            # so a quota-log hiccup here shouldn't undo the upload or
            # fail the request, only get logged.
            try:
                quota_service.increment_storage(user_id, size)
            except Exception:
                log.warning(
                    "quota increment_storage failed for user %s", user_id, exc_info=True
                )

            return (
                jsonify(
                    {
                        "document_id": uf.id,
                        "status": "PENDING",
                        "message": "Upload successful, processing started",
                    }
                ),
                201,
            )
        except Exception:
            db.rollback()
            try:
                storage_backend.delete(key)
            except Exception:
                pass
            raise
        finally:
            db.close()

    return bp
