"""Flask routes for workflow instrumentation + Research Workflow inspect (Bite 15)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Blueprint, jsonify, request, session

from backend.workflow.definitions import RESEARCH_PAPER_STEPS, WORKFLOW_ENGINE_VERSION
from backend.workflow.engine import get_engine
from backend.workflow.events import (
    WORKFLOW_EVENTS,
    emit_workflow_event_log,
    validate_workflow_event,
)


def persist_workflow_event(
    db: Any,
    *,
    WorkflowEvent: Any,
    user_id: int,
    project_id: int | None,
    event: str,
    meta: dict[str, Any] | None = None,
) -> Any:
    meta = meta or {}
    row = WorkflowEvent(
        user_id=user_id,
        project_id=project_id,
        event_name=event,
        meta_json=json.dumps(meta, ensure_ascii=False),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    emit_workflow_event_log(
        event=event, user_id=user_id, project_id=project_id, meta=meta
    )
    return row


def create_workflow_blueprint(
    *,
    SessionLocal: Any,
    Project: Any,
    WorkflowEvent: Any,
    select: Any,
    login_required: Callable,
    limiter: Any,
    UserFile: Any = None,
) -> Blueprint:
    bp = Blueprint("workflow_events", __name__)

    def _uid() -> int:
        return int(session["user_id"])

    @bp.post("/api/workflow-events")
    @login_required
    @limiter.limit("300 per hour")
    def create_workflow_event():
        uid = _uid()
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            payload = validate_workflow_event(data)
            project_id = payload.get("project_id")
            if project_id is not None:
                project_id = int(project_id)
                proj = db.execute(
                    select(Project).where(Project.id == project_id, Project.user_id == uid)
                ).scalar_one_or_none()
                if proj is None:
                    return jsonify({"error": "not_found", "detail": "project_not_found"}), 404
            row = persist_workflow_event(
                db,
                WorkflowEvent=WorkflowEvent,
                user_id=uid,
                project_id=project_id,
                event=payload["event"],
                meta=payload["meta"],
            )
            db.commit()
            return jsonify({"ok": True, "id": row.id, "event": payload["event"]}), 201
        except ValueError as exc:
            return jsonify({"error": "validation", "detail": str(exc)}), 422
        except (TypeError, ValueError):
            return jsonify({"error": "validation", "detail": "invalid_project_id"}), 422
        finally:
            db.close()

    @bp.get("/api/workflow-events/catalog")
    @login_required
    def workflow_event_catalog():
        return jsonify({"events": sorted(WORKFLOW_EVENTS)})

    @bp.get("/api/workflows/catalog")
    @login_required
    def research_workflow_catalog():
        """Named Research Workflow steps (inspect contract — not agents)."""
        return jsonify(
            {
                "engine_version": WORKFLOW_ENGINE_VERSION,
                "workflows": [
                    {
                        "name": "research_paper",
                        "steps": list(RESEARCH_PAPER_STEPS),
                    }
                ],
            }
        )

    @bp.get("/api/workflows/<workflow_id>")
    @login_required
    def get_research_workflow(workflow_id: str):
        uid = _uid()
        payload = get_engine().inspect(workflow_id)
        if payload is None or int(payload.get("user_id") or 0) != uid:
            return jsonify({"error": "not_found"}), 404
        return jsonify(payload)

    @bp.get("/api/workflows/by-file/<int:file_id>")
    @login_required
    def get_research_workflow_by_file(file_id: int):
        uid = _uid()
        if UserFile is not None:
            db = SessionLocal()
            try:
                uf = db.execute(
                    select(UserFile).where(UserFile.id == file_id, UserFile.user_id == uid)
                ).scalar_one_or_none()
                if uf is None:
                    return jsonify({"error": "not_found"}), 404
            finally:
                db.close()
        payload = get_engine().inspect_file(uid, file_id)
        if payload is None:
            return jsonify({"error": "not_found", "detail": "no_active_workflow"}), 404
        return jsonify(payload)

    @bp.get("/api/projects/<int:project_id>/workflows")
    @login_required
    def list_project_research_workflows(project_id: int):
        uid = _uid()
        db = SessionLocal()
        try:
            proj = db.execute(
                select(Project).where(Project.id == project_id, Project.user_id == uid)
            ).scalar_one_or_none()
            if proj is None:
                return jsonify({"error": "not_found"}), 404
        finally:
            db.close()
        rows = get_engine().list_for_project(uid, project_id)
        return jsonify(
            {
                "engine_version": WORKFLOW_ENGINE_VERSION,
                "project_id": project_id,
                "workflows": rows,
            }
        )

    return bp
