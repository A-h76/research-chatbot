"""EvidenceObject domain helpers and API DTO shaping."""

from __future__ import annotations

import json
from typing import Any


CONFIDENCE_BANDS = frozenset({"low", "moderate", "high"})
OBJECT_STATUSES = frozenset({"candidate", "accepted", "rejected", "superseded"})
RELATIONS = frozenset({"supports", "contradicts", "related"})


def parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _iso_ts(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        return value
    return None


def serialize_evidence_object(row: Any, *, relation: str | None = None, file_title: str | None = None) -> dict[str, Any]:
    """Project an ORM/row-like object into the public EvidenceObject DTO."""
    dto: dict[str, Any] = {
        "id": getattr(row, "id", None),
        "user_id": getattr(row, "user_id", None),
        "project_id": getattr(row, "project_id", None),
        "file_id": getattr(row, "file_id", None),
        "page": getattr(row, "page", None),
        "char_start": getattr(row, "char_start", None),
        "char_end": getattr(row, "char_end", None),
        "section": getattr(row, "section", "") or "",
        "quote": getattr(row, "quote", "") or "",
        "claim": getattr(row, "claim", "") or "",
        "study_type": getattr(row, "study_type", "") or "",
        "study_quality": getattr(row, "study_quality", "") or "",
        "supports": parse_json_list(getattr(row, "supports_json", None)),
        "contradicts": parse_json_list(getattr(row, "contradicts_json", None)),
        "limitations": parse_json_list(getattr(row, "limitations_json", None)),
        "confidence_band": getattr(row, "confidence_band", "low") or "low",
        "status": getattr(row, "status", "candidate") or "candidate",
        "pipeline_version": getattr(row, "pipeline_version", "") or "",
        "created_by": getattr(row, "created_by", "") or "",
        "content_hash": getattr(row, "content_hash", "") or "",
        "supersedes_id": getattr(row, "supersedes_id", None),
        "provenance": parse_json_object(getattr(row, "provenance_json", None)),
        "source_kg_node_id": getattr(row, "source_kg_node_id", "") or "",
        # Additive — Ranking (Sprint 2) uses for recency; optional for consumers
        "created_at": _iso_ts(getattr(row, "created_at", None)),
        "updated_at": _iso_ts(getattr(row, "updated_at", None)),
    }
    if relation:
        dto["relation"] = relation if relation in RELATIONS else "related"
    if file_title is not None:
        dto["file_title"] = file_title
    return dto


def require_page_anchor(*, file_id: int | None, quote: str | None, page: int | None) -> None:
    """Reject free-floating claims (Principle 0 / ADD hard rule)."""
    if not file_id:
        raise ValueError("evidence requires file_id")
    if not (quote and str(quote).strip()):
        raise ValueError("evidence requires non-empty quote")
    # page may be None only when caller records provenance gap; extractor should skip.
    _ = page
