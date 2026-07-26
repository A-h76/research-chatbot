"""Note rows (plain dicts) → research-context note payloads."""

from __future__ import annotations

from typing import Any


def adapt_notes(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Translate note dicts. Expects ORM already flattened at the source boundary."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        note_id = row.get("id")
        if note_id is None:
            continue
        out.append(
            {
                "id": note_id,
                "title": row.get("title") or "",
                "content": row.get("content") or "",
                "file_id": row.get("file_id"),
                "project_id": row.get("project_id"),
                "updated_at": row.get("updated_at"),
            }
        )
    return out
