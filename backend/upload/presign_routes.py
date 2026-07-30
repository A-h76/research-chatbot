"""Presigned upload routes extracted from server.py."""

from __future__ import annotations

import base64
import binascii
import logging
import math
import os
import shutil
import uuid

from flask import Blueprint, jsonify, request, send_file, session


def create_presign_upload_blueprint(
    *,
    SessionLocal,
    Project,
    UploadSession,
    UploadBatch,
    UserFile,
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    MAX_FILE_MB,
    MULTIPART_THRESHOLD_BYTES,
    UPLOAD_PART_BYTES,
    UPLOAD_SESSION_TTL_SECONDS,
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
    enqueue_job,
    upload_dir,
):
    bp = Blueprint("presign_upload_routes", __name__)

    @bp.route("/api/uploads/presign", methods=["POST"])
    @login_required
    @limiter.limit("60 per hour")
    def presign_upload():
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("filename") or "").strip()
        mime = data.get("mime") or "application/octet-stream"
        size = int(data.get("size") or 0)
        checksum = (data.get("checksum_sha256") or "").strip().lower() or None
        project_id = data.get("project_id")
        conversation_id = data.get("conversation_id")

        if not name or size <= 0:
            return jsonify({"error": "invalid_request"}), 400
        if size > MAX_UPLOAD_BYTES:
            return jsonify({"error": "too_large", "detail": f"Max file size is {MAX_FILE_MB} MB"}), 400
        try:
            ext = validate_extension(name, allowed=ALLOWED_EXTENSIONS)
            from backend.upload.magic_bytes import CANONICAL_MIME

            mime = CANONICAL_MIME.get(ext, mime)
        except UploadValidationError as exc:
            log_security_event("invalid_mime", code=exc.code, filename=name, message=exc.message)
            return jsonify({"error": exc.code, "detail": exc.message}), 400

        db = SessionLocal()
        try:
            project_id, project_denied = resolve_owned_project_id(
                db, Project, project_id, session["user_id"]
            )
            if project_denied:
                log_security_event(
                    "authz_denied",
                    resource="project",
                    action="presign",
                    user_id=session["user_id"],
                    project_id=data.get("project_id"),
                )

            if checksum:
                dup = find_duplicate_file(db, session["user_id"], checksum)
                if dup:
                    return jsonify({"duplicate": True, "file": file_to_dict(dup)})

            provider = storage.storage_manager.provider
            key = storage.storage_manager.new_key(os.path.splitext(name.lower())[1])
            use_multipart = provider.supports_multipart and size > MULTIPART_THRESHOLD_BYTES

            upload_session = UploadSession(
                user_id=session["user_id"],
                project_id=project_id,
                conversation_id=conversation_id,
                key=key,
                name=name[:300],
                mime=mime,
                size_expected=size,
                checksum_sha256=checksum,
                status="pending",
            )
            db.add(upload_session)
            db.commit()

            if use_multipart:
                upload_id = provider.create_multipart_upload(key, mime)
                upload_session.upload_id = upload_id
                db.commit()
                part_count = math.ceil(size / UPLOAD_PART_BYTES)
                parts = [
                    {
                        "part_number": i + 1,
                        "url": provider.presigned_part_url(key, upload_id, i + 1),
                    }
                    for i in range(part_count)
                ]
                return jsonify(
                    {
                        "mode": "multipart",
                        "session_id": upload_session.id,
                        "key": key,
                        "upload_id": upload_id,
                        "part_size": UPLOAD_PART_BYTES,
                        "parts": parts,
                    }
                )

            put_url = provider.presigned_put_url(key, mime, expires_in=UPLOAD_SESSION_TTL_SECONDS)
            return jsonify({"mode": "single", "session_id": upload_session.id, "key": key, "put_url": put_url})
        finally:
            db.close()

    @bp.route("/api/uploads/multipart/complete", methods=["POST"])
    @login_required
    def complete_multipart_upload_route():
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get("session_id")
        parts = data.get("parts") or []

        db = SessionLocal()
        try:
            upload_session = db.get(UploadSession, session_id)
            if not upload_session or upload_session.user_id != session["user_id"] or not upload_session.upload_id:
                return jsonify({"error": "not_found"}), 404

            provider = storage.storage_manager.provider
            try:
                provider.complete_multipart_upload(
                    upload_session.key,
                    upload_session.upload_id,
                    [storage.UploadPart(part_number=p["part_number"], etag=p["etag"]) for p in parts],
                )
            except Exception:
                logging.exception("multipart complete failed for session %s", session_id)
                provider.abort_multipart_upload(upload_session.key, upload_session.upload_id)
                upload_session.status = "aborted"
                db.commit()
                return jsonify({"error": "multipart_complete_failed"}), 502

            upload_session.status = "uploaded"
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.route("/api/uploads/confirm", methods=["POST"])
    @login_required
    @limiter.limit("60 per hour")
    def confirm_upload():
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get("session_id")
        content_md5_b64 = data.get("content_md5_b64")

        db = SessionLocal()
        try:
            upload_session = db.get(UploadSession, session_id)
            if not upload_session or upload_session.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if upload_session.status == "confirmed":
                return jsonify({"error": "already_confirmed"}), 409

            provider = storage.storage_manager.provider
            info = provider.head(upload_session.key)
            if info is None:
                return jsonify({"error": "object_not_found"}), 400
            if upload_session.size_expected and info.size != upload_session.size_expected:
                return jsonify({"error": "size_mismatch"}), 400

            if content_md5_b64 and not upload_session.upload_id and info.etag:
                expected_hex = binascii.hexlify(base64.b64decode(content_md5_b64)).decode()
                if expected_hex != info.etag:
                    provider.delete(upload_session.key)
                    upload_session.status = "aborted"
                    db.commit()
                    return jsonify({"error": "checksum_mismatch"}), 400

            if upload_session.checksum_sha256:
                dup = find_duplicate_file(db, session["user_id"], upload_session.checksum_sha256)
                if dup:
                    provider.delete(upload_session.key)
                    upload_session.status = "confirmed"
                    db.commit()
                    result = file_to_dict(dup)
                    result["note"] = None
                    result["duplicate"] = True
                    return jsonify(result)

            lower = upload_session.name.lower()
            ext = os.path.splitext(lower)[1]
            try:
                validate_extension(upload_session.name, allowed=ALLOWED_EXTENSIONS)
            except UploadValidationError as exc:
                provider.delete(upload_session.key)
                upload_session.status = "aborted"
                db.commit()
                log_security_event("invalid_mime", code=exc.code, filename=upload_session.name, message=exc.message)
                return jsonify({"error": exc.code, "detail": exc.message}), 400

            try:
                with provider.local_copy(upload_session.key, suffix=ext or ".bin") as local_path:
                    _, sniffed_mime = validate_upload_path(
                        local_path,
                        upload_session.name,
                        allowed=ALLOWED_EXTENSIONS,
                        size_bytes=info.size,
                        max_mb=MAX_FILE_MB,
                    )
            except UploadValidationError as exc:
                provider.delete(upload_session.key)
                upload_session.status = "aborted"
                db.commit()
                log_security_event("invalid_mime", code=exc.code, filename=upload_session.name, message=exc.message)
                return jsonify({"error": exc.code, "detail": exc.message}), 400
            except Exception:
                logging.exception("upload confirm content validation failed for session %s", session_id)
                provider.delete(upload_session.key)
                upload_session.status = "aborted"
                db.commit()
                return jsonify({"error": "validation_failed"}), 502

            kind = kind_for_extension(ext)
            uid = session["user_id"]
            user_file = UserFile(
                user_id=uid,
                project_id=upload_session.project_id,
                conversation_id=upload_session.conversation_id,
                name=upload_session.name,
                mime=sniffed_mime,
                kind=kind,
                path=upload_session.key,
                size=info.size,
                checksum_sha256=upload_session.checksum_sha256,
            )
            db.add(user_file)
            db.flush()
            upload_session.status = "confirmed"
            adjust_storage_usage(db, uid, delta_bytes=info.size, delta_files=1)

            job_id = None
            if kind == "document":
                batch = UploadBatch(
                    user_id=uid,
                    project_id=upload_session.project_id,
                    conversation_id=upload_session.conversation_id,
                    source="presign",
                    file_count=1,
                )
                db.add(batch)
                db.flush()
                job_id = enqueue_job(db, uid, user_file.id, "import", upload_batch_id=batch.id)

            db.commit()
            result = file_to_dict(user_file)
            result["note"] = None
            result["job_id"] = job_id
            return jsonify(result)
        finally:
            db.close()

    @bp.route("/api/uploads/local-put/<key>", methods=["PUT"])
    def local_upload_put(key):
        provider = storage.storage_manager.provider
        if not hasattr(provider, "verify_token"):
            return jsonify({"error": "not_supported"}), 404
        try:
            payload = provider.verify_token(request.args.get("token", ""), max_age=UPLOAD_SESSION_TTL_SECONDS)
        except ValueError:
            return jsonify({"error": "invalid_token"}), 403
        if payload.get("key") != key:
            return jsonify({"error": "invalid_token"}), 403

        tmp_path = os.path.join(upload_dir, "put_" + uuid.uuid4().hex)
        try:
            with open(tmp_path, "wb") as out:
                shutil.copyfileobj(request.stream, out)
            provider.upload(key, tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return jsonify({"ok": True})

    @bp.route("/api/uploads/local-get/<key>")
    def local_upload_get(key):
        provider = storage.storage_manager.provider
        if not hasattr(provider, "verify_token"):
            return jsonify({"error": "not_supported"}), 404
        try:
            payload = provider.verify_token(request.args.get("token", ""), max_age=300)
        except ValueError:
            return jsonify({"error": "invalid_token"}), 403
        if payload.get("key") != key:
            return jsonify({"error": "invalid_token"}), 403
        return send_file(
            provider.path_for(key),
            mimetype=payload.get("mime"),
            download_name=payload.get("name"),
            as_attachment=True,
        )

    return bp
