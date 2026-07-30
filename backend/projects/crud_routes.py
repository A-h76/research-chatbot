"""Project CRUD routes extracted from server.py.

Workspace hub/research/memory remain on create_projects_blueprint;
this module owns list/create/get/patch/delete only.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session


def create_project_crud_blueprint(
    *,
    SessionLocal,
    Project,
    Conversation,
    Memory,
    select_fn,
    login_required,
    project_service,
):
    bp = Blueprint("project_crud_routes", __name__)

    @bp.route("/api/projects", methods=["GET"])
    @login_required
    def list_projects():
        db = SessionLocal()
        try:
            projs = (
                db.execute(
                    select_fn(Project).where(Project.user_id == session["user_id"]).order_by(Project.created_at)
                )
                .scalars()
                .all()
            )
            return jsonify(
                [
                    {
                        "id": p.id,
                        "name": p.name,
                        "emoji": p.emoji,
                        "description": p.description or "",
                        "instructions": p.instructions or "",
                    }
                    for p in projs
                ]
            )
        finally:
            db.close()

    @bp.route("/api/projects", methods=["POST"])
    @login_required
    def create_project():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()[:100]
        if not name:
            return jsonify({"error": "name_required"}), 400
        db = SessionLocal()
        try:
            p = Project(
                user_id=session["user_id"],
                name=name,
                emoji=(data.get("emoji") or "📁")[:16],
                description=(data.get("description") or "")[:2000],
                instructions=(data.get("instructions") or "")[:4000],
            )
            db.add(p)
            db.commit()
            return jsonify(
                {
                    "id": p.id,
                    "name": p.name,
                    "emoji": p.emoji,
                    "description": p.description or "",
                    "instructions": p.instructions,
                }
            )
        finally:
            db.close()

    @bp.route("/api/projects/<int:pid>", methods=["GET"])
    @login_required
    def get_project(pid):
        detail = project_service.get_detail(pid, session["user_id"])
        if detail is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(detail)

    @bp.route("/api/projects/<int:pid>", methods=["PATCH"])
    @login_required
    def update_project(pid):
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            p = db.get(Project, pid)
            if not p or p.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if "name" in data:
                p.name = str(data["name"]).strip()[:100] or p.name
            if "emoji" in data:
                p.emoji = str(data["emoji"])[:16] or p.emoji
            if "description" in data:
                p.description = str(data["description"])[:2000]
            if "instructions" in data:
                p.instructions = str(data["instructions"])[:4000]
            db.commit()
            return jsonify(
                {
                    "id": p.id,
                    "name": p.name,
                    "emoji": p.emoji,
                    "description": p.description or "",
                    "instructions": p.instructions or "",
                }
            )
        finally:
            db.close()

    @bp.route("/api/projects/<int:pid>", methods=["DELETE"])
    @login_required
    def delete_project(pid):
        db = SessionLocal()
        try:
            p = db.get(Project, pid)
            if not p or p.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            for c in db.execute(select_fn(Conversation).where(Conversation.project_id == pid)).scalars():
                c.project_id = None
            for m in db.execute(select_fn(Memory).where(Memory.project_id == pid)).scalars():
                db.delete(m)
            db.delete(p)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    return bp
