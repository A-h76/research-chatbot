"""Conversation CRUD routes extracted from server.py (Phase 4).

Chat SSE (/api/chat) and memories remain separate slices.
"""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, request, session


VALID_REASONING_EFFORTS = ("low", "medium", "high")


def apply_conversation_settings(c, data):
    if "temperature" in data:
        t = data["temperature"]
        c.temperature = None if t is None else max(0.0, min(2.0, float(t)))
    if "reasoning_effort" in data:
        r = data["reasoning_effort"]
        c.reasoning_effort = r if r in VALID_REASONING_EFFORTS else None
    if "memory_enabled" in data:
        c.memory_enabled = 1 if data["memory_enabled"] else 0


def conversation_settings_json(c):
    return {
        "temperature": c.temperature,
        "reasoning_effort": c.reasoning_effort,
        "memory_enabled": (bool(c.memory_enabled) if c.memory_enabled is not None else True),
    }


def create_conversation_blueprint(
    *,
    SessionLocal,
    Conversation,
    Project,
    UserFile,
    select_fn,
    login_required,
    resolve_owned_project_id,
    log_security_event,
    get_models,
    default_model,
    remove_file_row,
):
    bp = Blueprint("conversation_routes", __name__)

    def _purge_conversation(db, convo):
        for uf in db.execute(select_fn(UserFile).where(UserFile.conversation_id == convo.id)).scalars().all():
            if uf.project_id:
                uf.conversation_id = None
            else:
                remove_file_row(db, uf)
        db.delete(convo)

    @bp.route("/api/conversations", methods=["GET"])
    @login_required
    def list_conversations():
        db = SessionLocal()
        try:
            convos = (
                db.execute(
                    select_fn(Conversation)
                    .where(Conversation.user_id == session["user_id"])
                    .order_by(Conversation.updated_at.desc())
                )
                .scalars()
                .all()
            )
            return jsonify(
                [
                    {
                        "id": c.id,
                        "title": c.title,
                        "model": c.model,
                        "project_id": c.project_id,
                        "file_id": c.file_id,
                    }
                    for c in convos
                ]
            )
        finally:
            db.close()

    @bp.route("/api/conversations", methods=["POST"])
    @login_required
    def create_conversation():
        data = request.get_json(silent=True) or {}
        model = data.get("model") or default_model
        if model not in get_models():
            model = default_model
        project_id = data.get("project_id")
        file_id = data.get("file_id")
        db = SessionLocal()
        try:
            if project_id:
                project_id, denied = resolve_owned_project_id(
                    db, Project, project_id, session["user_id"]
                )
                if denied:
                    log_security_event(
                        "authz_denied",
                        resource="project",
                        action="create_conversation",
                        user_id=session["user_id"],
                        project_id=data.get("project_id"),
                    )

            paper_title = None
            if file_id:
                uf = db.get(UserFile, file_id)
                if not uf or uf.user_id != session["user_id"]:
                    file_id = None
                else:
                    paper_title = uf.title or uf.name or None
                    if not project_id and uf.project_id:
                        inherited, inherited_denied = resolve_owned_project_id(
                            db, Project, uf.project_id, session["user_id"]
                        )
                        if inherited_denied:
                            log_security_event(
                                "authz_denied",
                                resource="project",
                                action="create_conversation_inherit",
                                user_id=session["user_id"],
                                project_id=uf.project_id,
                                file_id=file_id,
                            )
                        project_id = inherited

            c = Conversation(
                user_id=session["user_id"],
                model=model,
                project_id=project_id,
                file_id=file_id,
            )
            if paper_title and file_id:
                c.title = f"Chat: {paper_title}"[:200]
                c.title_generated = 0
            apply_conversation_settings(c, data)
            db.add(c)
            db.commit()
            return jsonify(
                {
                    "id": c.id,
                    "title": c.title,
                    "model": c.model,
                    "project_id": c.project_id,
                    "file_id": c.file_id,
                    **conversation_settings_json(c),
                }
            )
        finally:
            db.close()

    @bp.route("/api/conversations/<int:cid>", methods=["GET"])
    @login_required
    def get_conversation(cid):
        db = SessionLocal()
        try:
            c = db.get(Conversation, cid)
            if not c or c.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            return jsonify(
                {
                    "id": c.id,
                    "title": c.title,
                    "model": c.model,
                    "project_id": c.project_id,
                    "file_id": c.file_id,
                    **conversation_settings_json(c),
                    "messages": [
                        {
                            "id": m.id,
                            "role": m.role,
                            "content": m.content,
                            "sources": json.loads(m.sources) if m.sources else [],
                            "attachments": (json.loads(m.attachments) if m.attachments else []),
                        }
                        for m in c.messages
                    ],
                }
            )
        finally:
            db.close()

    @bp.route("/api/conversations/<int:cid>", methods=["PATCH"])
    @login_required
    def update_conversation(cid):
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            c = db.get(Conversation, cid)
            if not c or c.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if "title" in data:
                c.title = str(data["title"])[:200]
                c.title_generated = 1
            if "model" in data and data["model"] in get_models():
                c.model = data["model"]
            apply_conversation_settings(c, data)
            if "project_id" in data:
                pid = data["project_id"]
                if pid is None:
                    c.project_id = None
                else:
                    p = db.get(Project, pid)
                    if p and p.user_id == session["user_id"]:
                        c.project_id = pid
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.route("/api/conversations/<int:cid>", methods=["DELETE"])
    @login_required
    def delete_conversation(cid):
        db = SessionLocal()
        try:
            c = db.get(Conversation, cid)
            if not c or c.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            _purge_conversation(db, c)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.route("/api/conversations/delete", methods=["POST"])
    @login_required
    def bulk_delete_conversations():
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        db = SessionLocal()
        try:
            q = select_fn(Conversation).where(Conversation.user_id == uid)
            if not data.get("all"):
                ids = [int(i) for i in (data.get("ids") or [])]
                if not ids:
                    return jsonify({"error": "no_ids"}), 400
                q = q.where(Conversation.id.in_(ids))
            convos = db.execute(q).scalars().all()
            for c in convos:
                _purge_conversation(db, c)
            db.commit()
            log_security_event("chats_deleted", user=uid, count=len(convos), all=bool(data.get("all")))
            return jsonify({"ok": True, "deleted": len(convos)})
        finally:
            db.close()

    return bp
