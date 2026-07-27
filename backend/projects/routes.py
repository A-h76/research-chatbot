"""Project workspace HTTP routes.

Hub + questions + research (Sprint B) + memory (Sprint C).
Project CRUD remains on server.py until a later slice migrates those routes.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session


def create_projects_blueprint(
    *,
    project_service,
    project_research_service=None,
    memory_promotion_service=None,
    login_required,
    limiter=None,
):
    """Factory — inject services + session ``login_required``."""
    bp = Blueprint("projects_workspace", __name__, url_prefix="/api/projects")

    def _rate_limit(spec: str):
        def decorator(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return decorator

    @bp.route("/<int:pid>/hub", methods=["GET"])
    @login_required
    def get_project_hub(pid: int):
        uid = session["user_id"]
        hub = project_service.get_hub(pid, uid)
        if hub is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(hub)

    @bp.route("/<int:pid>/insights", methods=["GET"])
    @login_required
    def list_project_insights(pid: int):
        result = project_service.list_insights(pid, session["user_id"])
        if result is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(result)

    @bp.route("/<int:pid>/questions", methods=["GET"])
    @login_required
    def list_project_questions(pid: int):
        uid = session["user_id"]
        status = request.args.get("status") or None
        result = project_service.list_questions(pid, uid, status=status)
        if result is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(result)

    @bp.route("/<int:pid>/questions", methods=["POST"])
    @login_required
    def create_project_question(pid: int):
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        payload, err = project_service.create_question(
            pid,
            uid,
            text=str(data.get("text") or ""),
            status=str(data.get("status") or "open"),
            source=str(data.get("source") or "manual"),
        )
        if err == "not_found":
            return jsonify({"error": "not_found"}), 404
        if err == "text_required":
            return jsonify({"error": "text_required", "detail": "Question text is required."}), 400
        return jsonify(payload), 201

    @bp.route("/<int:pid>/questions/<int:qid>", methods=["PATCH"])
    @login_required
    def update_project_question(pid: int, qid: int):
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        kwargs: dict = {}
        if "text" in data:
            kwargs["text"] = str(data.get("text") or "")
        if "status" in data:
            kwargs["status"] = str(data.get("status") or "")
        payload, err = project_service.update_question(pid, qid, uid, **kwargs)
        if err == "not_found":
            return jsonify({"error": "not_found"}), 404
        if err == "text_required":
            return jsonify({"error": "text_required"}), 400
        if err == "invalid_status":
            return jsonify({"error": "invalid_status"}), 400
        return jsonify(payload)

    @bp.route("/<int:pid>/questions/<int:qid>", methods=["DELETE"])
    @login_required
    def delete_project_question(pid: int, qid: int):
        err = project_service.delete_question(pid, qid, session["user_id"])
        if err == "not_found":
            return jsonify({"error": "not_found"}), 404
        return jsonify({"ok": True})

    if memory_promotion_service is not None:

        @bp.route("/<int:pid>/memory", methods=["GET"])
        @login_required
        def list_project_memory(pid: int):
            kind = request.args.get("kind") or None
            source = request.args.get("source") or None
            pinned_raw = request.args.get("pinned")
            pinned = None
            if pinned_raw is not None:
                pinned = pinned_raw.strip().lower() in ("1", "true", "yes")
            result = memory_promotion_service.list_memories(
                pid,
                session["user_id"],
                kind=kind,
                source=source,
                pinned=pinned,
            )
            if result is None:
                return jsonify({"error": "not_found"}), 404
            return jsonify(result)

        @bp.route("/<int:pid>/memory/<int:mid>", methods=["PATCH"])
        @login_required
        def patch_project_memory(pid: int, mid: int):
            data = request.get_json(silent=True) or {}
            action = str(data.get("action") or "").strip()
            payload, err = memory_promotion_service.update_memory(
                pid, mid, session["user_id"], action=action
            )
            if err == "not_found":
                return jsonify({"error": "not_found"}), 404
            if err == "invalid_action":
                return (
                    jsonify(
                        {
                            "error": "invalid_action",
                            "detail": "Use action: pin|unpin|archive|restore",
                        }
                    ),
                    400,
                )
            return jsonify(payload)

        @bp.route("/<int:pid>/memory/<int:mid>", methods=["DELETE"])
        @login_required
        def delete_project_memory(pid: int, mid: int):
            err = memory_promotion_service.soft_delete(pid, mid, session["user_id"])
            if err == "not_found":
                return jsonify({"error": "not_found"}), 404
            return jsonify({"ok": True})

    if project_research_service is not None:

        @bp.route("/<int:pid>/research", methods=["GET"])
        @login_required
        def list_project_research(pid: int):
            result = project_research_service.list_research(pid, session["user_id"])
            if result is None:
                return jsonify({"error": "not_found"}), 404
            return jsonify(result)

        @bp.route("/<int:pid>/research", methods=["POST"])
        @login_required
        @_rate_limit("5 per minute")
        def start_project_research(pid: int):
            data = request.get_json(silent=True) or {}
            preset = data.get("preset")
            if preset is not None:
                preset = str(preset).strip() or None
            query = str(data.get("query") or "").strip()
            raw_ids = data.get("file_ids")
            file_ids = [int(i) for i in (raw_ids or []) if i] if raw_ids else None
            force = bool(data.get("force"))

            payload, err = project_research_service.start_research(
                pid,
                session["user_id"],
                preset=preset,
                query=query,
                file_ids=file_ids,
                force=force,
            )
            if err == "not_found":
                return jsonify({"error": "not_found"}), 404
            if err == "invalid_preset":
                return jsonify({"error": "invalid_preset"}), 400
            if err == "preset_or_query_required":
                return (
                    jsonify(
                        {
                            "error": "preset_or_query_required",
                            "detail": "Provide a preset or a freeform query.",
                        }
                    ),
                    400,
                )
            if err == "too_few_ready":
                return (
                    jsonify(
                        {
                            "error": "too_few_ready",
                            "detail": "At least 2 papers need a completed analysis.",
                        }
                    ),
                    400,
                )
            if err == "too_many":
                return jsonify({"error": "too_many", "detail": "Maximum 10 papers."}), 400
            if err == "too_many_active":
                return (
                    jsonify(
                        {
                            "error": "too_many_active",
                            "detail": "Please wait until your current research finishes (max 2 active).",
                        }
                    ),
                    429,
                )
            if err in {
                "ai_disabled",
                "email_unverified",
                "account_inactive",
                "token_quota_exceeded",
                "cost_quota_exceeded",
                "daily_budget_exceeded",
                "ai_denied",
            }:
                status = 503 if err == "ai_disabled" else 429
                if err in {"email_unverified", "account_inactive"}:
                    status = 403
                return jsonify({"error": err, "detail": "AI request blocked."}), status
            return jsonify(payload)

        @bp.route("/<int:pid>/research/<int:rid>", methods=["GET"])
        @login_required
        def get_project_research(pid: int, rid: int):
            result = project_research_service.get_research(pid, session["user_id"], rid)
            if result is None:
                return jsonify({"error": "not_found"}), 404
            return jsonify(result)

    return bp
