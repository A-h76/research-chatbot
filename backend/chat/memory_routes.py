"""Memory CRUD routes extracted from server.py (Phase 4).

Chat SSE (/api/chat) remains deferred pending responsibility review.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session


def create_memory_blueprint(
    *,
    SessionLocal,
    Memory,
    select_fn,
    login_required,
):
    bp = Blueprint("memory_routes", __name__)

    @bp.route("/api/memories", methods=["GET"])
    @login_required
    def list_memories():
        db = SessionLocal()
        try:
            mems = (
                db.execute(
                    select_fn(Memory).where(Memory.user_id == session["user_id"]).order_by(Memory.created_at.desc())
                )
                .scalars()
                .all()
            )
            return jsonify(
                [
                    {
                        "id": m.id,
                        "fact": m.fact,
                        "project_id": m.project_id,
                        "importance": m.importance,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in mems
                ]
            )
        finally:
            db.close()

    @bp.route("/api/memories/<int:mid>", methods=["PATCH"])
    @login_required
    def update_memory(mid):
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            m = db.get(Memory, mid)
            if not m or m.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if "fact" in data:
                src = getattr(m, "source", None) or "chat"
                if src != "manual" and src != "chat":
                    return jsonify({"error": "immutable", "detail": "AI research memories cannot be edited."}), 400
                m.fact = str(data["fact"])[:1000]
            if "importance" in data:
                m.importance = max(1, min(5, int(data["importance"])))
            db.commit()
            return jsonify(
                {
                    "id": m.id,
                    "fact": m.fact,
                    "project_id": m.project_id,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat(),
                }
            )
        finally:
            db.close()

    @bp.route("/api/memories/<int:mid>", methods=["DELETE"])
    @login_required
    def delete_memory(mid):
        db = SessionLocal()
        try:
            m = db.get(Memory, mid)
            if not m or m.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            db.delete(m)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    return bp
