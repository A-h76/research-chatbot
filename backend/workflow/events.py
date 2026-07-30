"""Phase A.6 — researcher workflow instrumentation (not a polished analytics product).

Events are append-only breadcrumbs so Private Alpha can answer:
  - how many evidence objects accepted/rejected
  - draft generate / regenerate
  - export completed
  - where the workflow was abandoned

Never log quote/claim/manuscript body text.
"""

from __future__ import annotations

import logging
from typing import Any

WORKFLOW_EVENTS = frozenset(
    {
        "project_created",
        "papers_uploaded",
        "evidence_extracted",
        "evidence_accepted",
        "evidence_rejected",
        "decision_recorded",
        "draft_generated",
        "draft_regenerated",
        "reviewer_opened",
        "export_completed",
        "workflow_abandoned",
        "analysis_view_opened",
    }
)

_log = logging.getLogger("backend.workflow")


def validate_workflow_event(payload: dict[str, Any]) -> dict[str, Any]:
    name = (payload.get("event") or payload.get("name") or "").strip()
    if name not in WORKFLOW_EVENTS:
        raise ValueError(f"unknown workflow event: {name}")
    meta = payload.get("meta") or payload.get("properties") or {}
    if not isinstance(meta, dict):
        raise ValueError("meta must be an object")
    safe_meta = {
        k: v
        for k, v in meta.items()
        if k
        not in {
            "quote",
            "claim",
            "selected_text",
            "content",
            "body",
            "paragraph",
            "manuscript",
        }
    }
    return {
        "event": name,
        "project_id": payload.get("project_id"),
        "meta": safe_meta,
    }


def emit_workflow_event_log(
    *, event: str, user_id: int, project_id: int | None, meta: dict[str, Any]
) -> None:
    _log.info(
        "workflow_event",
        extra={
            "workflow_event": {
                "event": event,
                "user_id": user_id,
                "project_id": project_id,
                "meta": meta,
            }
        },
    )
