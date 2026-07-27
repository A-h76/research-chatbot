"""Citation rows (plain dicts) → research-context citation payloads."""

from __future__ import annotations

from typing import Any


def adapt_citations(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Translate citation dicts. Expects ORM already flattened at the source boundary."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        cite_id = row.get("id")
        if cite_id is None:
            continue
        out.append(
            {
                "id": cite_id,
                "title": row.get("title") or "",
                "authors": row.get("authors") or "",
                "year": row.get("year") or "",
                "venue": row.get("venue") or "",
                "doi": row.get("doi") or "",
                "url": row.get("url") or "",
                "project_id": row.get("project_id"),
            }
        )
    return out
