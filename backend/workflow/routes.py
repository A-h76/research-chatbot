"""Flask routes for Phase A.6 workflow instrumentation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Blueprint, jsonify, request, session

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

    return bp
