"""Flask routes for Assistant Engine (ADR-0018) — never import server."""

from __future__ import annotations

from typing import Any, Callable

from flask import Blueprint, jsonify, request, session


def create_assistant_blueprint(
    *,
    assistant_engine: Any,
    login_required: Callable,
    limiter: Any,
) -> Blueprint:
    bp = Blueprint("assistant", __name__)

    def _uid() -> int:
        return int(session["user_id"])

    @bp.get("/api/assistant/research-state")
    @login_required
    @limiter.limit("120 per hour")
    def get_research_state():
        uid = _uid()
        raw_pid = request.args.get("project_id")
        project_id = int(raw_pid) if raw_pid not in (None, "") else None
        try:
            state = assistant_engine.research_state(uid, project_id)
        except LookupError as exc:
            code = str(exc)
            status = 404 if "not_found" in code else 400
            return jsonify({"error": code}), status
        from backend.assistant.research_state import research_state_to_dict

        return jsonify(research_state_to_dict(state))

    @bp.get("/api/assistant/session")
    @login_required
    @limiter.limit("120 per hour")
    def open_session():
        uid = _uid()
        raw_pid = request.args.get("project_id")
        project_id = int(raw_pid) if raw_pid not in (None, "") else None
        try:
            payload = assistant_engine.open_session(uid, project_id)
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify(payload)

    @bp.post("/api/assistant/turn")
    @login_required
    @limiter.limit("120 per hour")
    def assistant_turn():
        uid = _uid()
        data = request.get_json(silent=True) or {}
        message = str(data.get("message") or "")
        raw_pid = data.get("project_id")
        project_id = int(raw_pid) if raw_pid not in (None, "") else None
        surface = str(data.get("surface") or "home")
        conversation_id = data.get("conversation_id")
        if conversation_id is not None:
            try:
                conversation_id = int(conversation_id)
            except (TypeError, ValueError):
                conversation_id = None
        try:
            payload = assistant_engine.turn(
                user_id=uid,
                message=message,
                project_id=project_id,
                surface=surface,
                conversation_id=conversation_id,
            )
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify(payload)

    return bp
