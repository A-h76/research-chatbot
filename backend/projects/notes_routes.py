"""Notes API routes extracted from server.py.

This module preserves behavior while reducing monolith surface area.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session


def create_notes_blueprint(
    *,
    SessionLocal,
    Note,
    Project,
    UserFile,
    select_fn,
    login_required,
    resolve_owned_project_id,
    log_security_event,
):
    bp = Blueprint("notes_routes", __name__)

    def _note_to_dict(note):
        return {
            "id": note.id,
            "title": note.title or "",
            "content": note.content or "",
            "project_id": note.project_id,
            "file_id": note.file_id,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }

    @bp.route("/api/notes", methods=["GET"])
    @login_required
    def list_notes():
        uid = session["user_id"]
        args = request.args

        project_id_raw = args.get("project_id")
        file_id_raw = args.get("file_id", type=int)
        q = args.get("q", "").strip().lower() or None
        try:
            limit = max(1, min(500, int(args.get("limit", 200))))
            offset = max(0, int(args.get("offset", 0)))
        except (TypeError, ValueError):
            limit, offset = 200, 0

        db = SessionLocal()
        try:
            stmt = select_fn(Note).where(Note.user_id == uid)

            if project_id_raw is not None:
                try:
                    pid = int(project_id_raw)
                    stmt = stmt.where(Note.project_id == pid if pid else Note.project_id.is_(None))
                except (TypeError, ValueError):
                    pass

            if file_id_raw is not None:
                stmt = stmt.where(Note.file_id == file_id_raw)

            notes = db.execute(stmt.order_by(Note.updated_at.desc())).scalars().all()

            if q:
                notes = [n for n in notes if q in (n.title or "").lower() or q in (n.content or "").lower()]

            total = len(notes)
            page = notes[offset : offset + limit]

            return jsonify(
                {
                    "total": total,
                    "offset": offset,
                    "limit": limit,
                    "items": [_note_to_dict(n) for n in page],
                }
            )
        finally:
            db.close()

    @bp.route("/api/notes", methods=["POST"])
    @login_required
    def create_note():
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]

        content = str(data.get("content") or "").strip()
        if not content:
            return (
                jsonify({"error": "content_required", "detail": "Note content cannot be empty."}),
                400,
            )

        title = str(data.get("title") or "")[:300]
        project_id = data.get("project_id")
        file_id = data.get("file_id")

        db = SessionLocal()
        try:
            if project_id:
                project_id, denied = resolve_owned_project_id(db, Project, project_id, uid)
                if denied:
                    log_security_event(
                        "authz_denied",
                        resource="project",
                        action="create_note",
                        user_id=uid,
                        project_id=data.get("project_id"),
                    )

            if file_id:
                file_obj = db.get(UserFile, file_id)
                if not file_obj or file_obj.user_id != uid:
                    file_id = None
                elif not project_id and file_obj.project_id:
                    inherited, inherited_denied = resolve_owned_project_id(
                        db, Project, file_obj.project_id, uid
                    )
                    if inherited_denied:
                        log_security_event(
                            "authz_denied",
                            resource="project",
                            action="create_note_inherit",
                            user_id=uid,
                            project_id=file_obj.project_id,
                            file_id=file_id,
                        )
                    project_id = inherited

            note = Note(
                user_id=uid,
                title=title,
                content=content[:50000],
                project_id=project_id,
                file_id=file_id,
            )
            db.add(note)
            db.commit()
            return jsonify(_note_to_dict(note)), 201
        finally:
            db.close()

    @bp.route("/api/notes/<int:nid>", methods=["GET"])
    @login_required
    def get_note(nid):
        db = SessionLocal()
        try:
            note = db.get(Note, nid)
            if not note or note.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            return jsonify(_note_to_dict(note))
        finally:
            db.close()

    @bp.route("/api/notes/<int:nid>", methods=["PATCH"])
    @login_required
    def update_note(nid):
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            note = db.get(Note, nid)
            if not note or note.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if "title" in data:
                note.title = str(data["title"] or "")[:300]
            if "content" in data:
                note.content = str(data["content"] or "")[:50000]
            if "project_id" in data:
                pid = data["project_id"]
                if pid is None:
                    note.project_id = None
                else:
                    project = db.get(Project, pid)
                    if project and project.user_id == session["user_id"]:
                        note.project_id = pid
            if "file_id" in data:
                fid = data["file_id"]
                if fid is None:
                    note.file_id = None
                else:
                    file_obj = db.get(UserFile, fid)
                    if file_obj and file_obj.user_id == session["user_id"]:
                        note.file_id = fid
            note.updated_at = datetime.now(timezone.utc)
            db.commit()
            return jsonify(_note_to_dict(note))
        finally:
            db.close()

    @bp.route("/api/notes/<int:nid>", methods=["DELETE"])
    @login_required
    def delete_note(nid):
        db = SessionLocal()
        try:
            note = db.get(Note, nid)
            if not note or note.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            db.delete(note)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    return bp
