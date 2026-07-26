"""Project row (plain dict) → research-context project payload."""

from __future__ import annotations

from typing import Any


def adapt_project(row: dict[str, Any] | None) -> dict[str, Any]:
    """Translate a project dict. Empty dict when missing."""
    if not row or not isinstance(row, dict):
        return {}
    project_id = row.get("id")
    if project_id is None:
        return {}
    return {
        "id": project_id,
        "name": row.get("name") or "",
        "emoji": row.get("emoji") or "",
        "description": row.get("description") or "",
        "instructions": row.get("instructions") or "",
    }
