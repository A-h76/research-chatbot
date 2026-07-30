"""Writing document API routes extracted from server.py."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session


def create_writing_document_blueprint(
    *,
    SessionLocal,
    WritingDocument,
    WritingDocumentVersion,
    Project,
    select_fn,
    login_required,
    limiter,
    WritingDomainError,
    normalize_status_filter,
    require_owned_project,
    writing_doc_to_dict,
    normalize_document_mutation,
    normalize_editor_kind,
    resolve_owned_project_id,
    log_security_event,
    doc_hash_fn,
    word_count_fn,
    append_document_version,
    log_document_activity,
    emit_writing_observability,
    require_owned_document,
    build_version_conflict_payload,
    apply_writing_status_transition,
    next_version_number,
    normalize_idempotency_key,
    is_idempotent_replay,
    writing_doc_version_to_dict,
):
    bp = Blueprint("writing_document_routes", __name__)

    @bp.route("/api/writing/documents", methods=["GET"])
    @login_required
    def list_writing_documents():
        uid = session["user_id"]
        args = request.args
        project_id_raw = args.get("project_id")
        include_archived = str(args.get("include_archived") or "").lower() in {"1", "true", "yes"}
        include_deleted = str(args.get("include_deleted") or "").lower() in {"1", "true", "yes"}
        try:
            status_filter = normalize_status_filter(args.get("status"))
        except WritingDomainError as exc:
            return jsonify({"error": exc.code, "detail": exc.detail}), 400
        try:
            limit = max(1, min(200, int(args.get("limit", 50))))
        except (TypeError, ValueError):
            limit = 50

        db = SessionLocal()
        try:
            stmt = select_fn(WritingDocument).where(WritingDocument.user_id == uid)
            if not include_archived:
                stmt = stmt.where(WritingDocument.status != "archived")
            if not include_deleted:
                stmt = stmt.where(WritingDocument.status != "deleted")
            if project_id_raw is None:
                return jsonify({"error": "project_id_required", "detail": "project_id is required."}), 400
            try:
                pid = int(project_id_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid_project_id"}), 400
            try:
                require_owned_project(db, Project, user_id=uid, project_id=pid)
            except WritingDomainError:
                return jsonify({"error": "not_found"}), 404
            stmt = stmt.where(WritingDocument.project_id == pid)
            if status_filter:
                stmt = stmt.where(WritingDocument.status == status_filter)
            docs = db.execute(stmt.order_by(WritingDocument.updated_at.desc()).limit(limit)).scalars().all()
            return jsonify({"items": [writing_doc_to_dict(d) for d in docs], "count": len(docs)})
        finally:
            db.close()

    @bp.route("/api/writing/documents", methods=["POST"])
    @login_required
    @limiter.limit("30 per hour")
    def create_writing_document():
        uid = session["user_id"]
        data = request.get_json(silent=True) or {}
        try:
            normalized = normalize_document_mutation(
                str(data.get("title") or "Untitled draft"),
                str(data.get("content") or ""),
            )
        except WritingDomainError as exc:
            return jsonify({"error": exc.code, "detail": exc.detail}), 400
        title = normalized.title or "Untitled draft"
        content = normalized.content
        editor_kind = normalize_editor_kind(data.get("editor_kind"))

        project_id = data.get("project_id")
        if project_id is None:
            return jsonify({"error": "project_id_required", "detail": "Documents must belong to a project."}), 400
        db = SessionLocal()
        try:
            project_id, denied = resolve_owned_project_id(db, Project, project_id, uid)
            if denied or project_id is None:
                log_security_event(
                    "authz_denied",
                    resource="project",
                    action="create_writing_document",
                    user_id=uid,
                    project_id=data.get("project_id"),
                )
                return jsonify({"error": "forbidden"}), 403

            doc = WritingDocument(
                user_id=uid,
                project_id=project_id,
                title=title,
                content=content,
                editor_kind=editor_kind,
                current_version=1,
                last_saved_hash=doc_hash_fn(content),
                word_count=word_count_fn(content),
                status="draft",
            )
            db.add(doc)
            db.flush()
            append_document_version(db, uid=uid, doc=doc, source="create")
            log_document_activity(db, uid=uid, document_id=doc.id, action="create")
            db.commit()
            emit_writing_observability("DocumentCreated", uid=uid, doc=doc)
            return jsonify(writing_doc_to_dict(doc)), 201
        finally:
            db.close()

    @bp.route("/api/writing/documents/<int:doc_id>", methods=["GET"])
    @login_required
    def get_writing_document(doc_id):
        db = SessionLocal()
        try:
            try:
                doc = require_owned_document(
                    db,
                    WritingDocument,
                    user_id=session["user_id"],
                    document_id=doc_id,
                )
            except WritingDomainError:
                return jsonify({"error": "not_found"}), 404
            doc.last_opened_at = datetime.now(timezone.utc)
            db.commit()
            return jsonify(writing_doc_to_dict(doc))
        finally:
            db.close()

    @bp.route("/api/writing/documents/<int:doc_id>", methods=["PATCH"])
    @login_required
    @limiter.limit("120 per hour")
    def update_writing_document(doc_id):
        uid = session["user_id"]
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            try:
                doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=doc_id)
            except WritingDomainError:
                return jsonify({"error": "not_found"}), 404

            client_version = data.get("current_version")
            if client_version is not None and int(client_version) != int(doc.current_version or 1):
                log_security_event(
                    "version_conflict",
                    resource="writing_document",
                    action="update_writing_document",
                    user_id=uid,
                    document_id=doc_id,
                )
                return jsonify(build_version_conflict_payload(int(doc.current_version or 1))), 409

            if (doc.status or "") == "deleted" and any(k in data for k in ("title", "content", "editor_kind")):
                return jsonify({"error": "validation_error", "detail": "deleted_documents_are_read_only"}), 400

            if "title" in data:
                try:
                    normalized = normalize_document_mutation(str(data.get("title") or ""), doc.content or "")
                except WritingDomainError as exc:
                    return jsonify({"error": exc.code, "detail": exc.detail}), 400
                doc.title = normalized.title
            if "editor_kind" in data:
                doc.editor_kind = normalize_editor_kind(data.get("editor_kind"))
            if "status" in data:
                status = str(data.get("status") or "draft").strip().lower()
                try:
                    apply_writing_status_transition(doc, status)
                except WritingDomainError as exc:
                    return jsonify({"error": exc.code, "detail": exc.detail}), 400
            if "project_id" in data:
                raw_pid = data.get("project_id")
                if raw_pid is None:
                    return jsonify({"error": "project_id_required"}), 400
                pid, denied = resolve_owned_project_id(db, Project, raw_pid, uid)
                if denied or pid is None:
                    return jsonify({"error": "forbidden"}), 403
                doc.project_id = pid
            if "content" in data:
                try:
                    normalized = normalize_document_mutation(doc.title or "", str(data.get("content") or ""))
                except WritingDomainError as exc:
                    return jsonify({"error": exc.code, "detail": exc.detail}), 400
                next_content = normalized.content
                next_hash = doc_hash_fn(next_content)
                if next_hash != (doc.last_saved_hash or ""):
                    doc.content = next_content
                    doc.last_saved_hash = next_hash
                    doc.word_count = word_count_fn(next_content)
                    doc.current_version = next_version_number(doc.current_version)
                    append_document_version(db, uid=uid, doc=doc, source="save")
                    if doc.status == "draft":
                        apply_writing_status_transition(doc, "active")

            doc.updated_at = datetime.now(timezone.utc)
            log_document_activity(db, uid=uid, document_id=doc.id, action="update")
            db.commit()
            emit_writing_observability("DocumentUpdated", uid=uid, doc=doc)
            return jsonify(writing_doc_to_dict(doc))
        finally:
            db.close()

    @bp.route("/api/writing/documents/<int:doc_id>/autosave", methods=["POST"])
    @login_required
    @limiter.limit("120 per hour")
    def autosave_writing_document(doc_id):
        uid = session["user_id"]
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            try:
                doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=doc_id)
            except WritingDomainError:
                return jsonify({"error": "not_found"}), 404

            try:
                idempotency_key = normalize_idempotency_key(data.get("idempotency_key"))
            except WritingDomainError as exc:
                return jsonify({"error": exc.code, "detail": exc.detail}), 400

            if is_idempotent_replay(doc.last_autosave_key, idempotency_key):
                emit_writing_observability(
                    "DocumentAutosaveReplay",
                    uid=uid,
                    doc=doc,
                    metadata={"idempotency_key": idempotency_key},
                )
                return jsonify(
                    {
                        "ok": True,
                        "unchanged": True,
                        "idempotent_replay": True,
                        "document": writing_doc_to_dict(doc),
                    }
                )

            client_version = data.get("current_version")
            if client_version is not None and int(client_version) != int(doc.current_version or 1):
                return jsonify(build_version_conflict_payload(int(doc.current_version or 1))), 409

            if (doc.status or "") == "deleted":
                return jsonify({"error": "validation_error", "detail": "deleted_documents_are_read_only"}), 400

            try:
                normalized = normalize_document_mutation(
                    str(data.get("title") or doc.title or ""),
                    str(data.get("content") or ""),
                )
            except WritingDomainError as exc:
                return jsonify({"error": exc.code, "detail": exc.detail}), 400
            next_content = normalized.content
            next_title = normalized.title
            next_hash = doc_hash_fn(next_content)
            changed = next_hash != (doc.last_saved_hash or "") or next_title != (doc.title or "")
            if not changed:
                return jsonify({"ok": True, "unchanged": True, "document": writing_doc_to_dict(doc)})

            doc.content = next_content
            doc.title = next_title
            doc.last_saved_hash = next_hash
            doc.last_autosave_key = idempotency_key
            doc.word_count = word_count_fn(next_content)
            doc.current_version = next_version_number(doc.current_version)
            doc.updated_at = datetime.now(timezone.utc)
            if doc.status == "draft":
                apply_writing_status_transition(doc, "active")
            append_document_version(db, uid=uid, doc=doc, source="autosave")
            log_document_activity(
                db,
                uid=uid,
                document_id=doc.id,
                action="autosave",
                meta={"bytes": len(next_content)},
            )
            db.commit()
            emit_writing_observability(
                "DocumentAutosaved",
                uid=uid,
                doc=doc,
                metadata={"idempotency_key": idempotency_key},
            )
            return jsonify(
                {
                    "ok": True,
                    "unchanged": False,
                    "idempotent_replay": False,
                    "document": writing_doc_to_dict(doc),
                }
            )
        finally:
            db.close()

    @bp.route("/api/writing/documents/<int:doc_id>/versions", methods=["GET"])
    @login_required
    def list_writing_document_versions(doc_id):
        uid = session["user_id"]
        db = SessionLocal()
        try:
            try:
                require_owned_document(db, WritingDocument, user_id=uid, document_id=doc_id)
            except WritingDomainError:
                return jsonify({"error": "not_found"}), 404
            versions = (
                db.execute(
                    select_fn(WritingDocumentVersion)
                    .where(WritingDocumentVersion.document_id == doc_id, WritingDocumentVersion.user_id == uid)
                    .order_by(WritingDocumentVersion.version_no.desc())
                    .limit(100)
                )
                .scalars()
                .all()
            )
            return jsonify({"items": [writing_doc_version_to_dict(v) for v in versions], "count": len(versions)})
        finally:
            db.close()

    @bp.route("/api/writing/documents/<int:doc_id>/restore", methods=["POST"])
    @login_required
    @limiter.limit("30 per hour")
    def restore_writing_document_version(doc_id):
        uid = session["user_id"]
        data = request.get_json(silent=True) or {}
        version_id = data.get("version_id")
        if not version_id:
            return jsonify({"error": "version_id_required"}), 400

        db = SessionLocal()
        try:
            try:
                doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=doc_id)
            except WritingDomainError:
                return jsonify({"error": "not_found"}), 404
            if (doc.status or "") == "deleted":
                return jsonify({"error": "validation_error", "detail": "deleted_documents_cannot_be_restored_in_place"}), 400
            version = db.get(WritingDocumentVersion, int(version_id))
            if not version or version.user_id != uid or version.document_id != doc_id:
                return jsonify({"error": "not_found"}), 404

            doc.title = (version.title or "")[:300]
            doc.content = (version.content or "")[:200000]
            doc.last_saved_hash = doc_hash_fn(doc.content or "")
            doc.word_count = word_count_fn(doc.content or "")
            doc.current_version = next_version_number(doc.current_version)
            doc.updated_at = datetime.now(timezone.utc)
            append_document_version(db, uid=uid, doc=doc, source="restore")
            log_document_activity(
                db,
                uid=uid,
                document_id=doc.id,
                action="restore",
                meta={"from_version_id": int(version_id)},
            )
            db.commit()
            emit_writing_observability(
                "DocumentRestored",
                uid=uid,
                doc=doc,
                metadata={"restored_from_version_id": int(version_id)},
            )
            payload = writing_doc_to_dict(doc)
            payload["restored_from_version_id"] = int(version_id)
            return jsonify(payload)
        finally:
            db.close()

    return bp
