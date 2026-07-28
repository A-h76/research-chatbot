"""Sentence/block ↔ EvidenceObject bindings helpers."""

from __future__ import annotations

from typing import Any

from .objects import RELATIONS


def validate_binding_payload(payload: dict[str, Any]) -> dict[str, Any]:
    evidence_object_id = payload.get("evidence_object_id")
    if not evidence_object_id:
        raise ValueError("evidence_object_id is required")
    block_id = (payload.get("block_id") or "").strip()
    range_start = payload.get("range_start")
    range_end = payload.get("range_end")
    if not block_id and (range_start is None or range_end is None):
        raise ValueError("block_id or range_start/range_end required")
    relation = (payload.get("relation") or "supports").strip()
    if relation not in RELATIONS:
        raise ValueError(f"invalid relation: {relation}")
    return {
        "evidence_object_id": int(evidence_object_id),
        "block_id": block_id,
        "range_start": range_start,
        "range_end": range_end,
        "selected_text": (payload.get("selected_text") or "")[:2000],
        "relation": relation,
    }
