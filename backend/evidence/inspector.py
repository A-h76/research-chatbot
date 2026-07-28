"""Explain / Inspector assembly — stored evidence only (Principle 0)."""

from __future__ import annotations

from typing import Any, Iterable

from .objects import serialize_evidence_object


def compute_sufficiency(evidence_rows: Iterable[dict[str, Any]]) -> str:
    rows = list(evidence_rows)
    if not rows:
        return "insufficient"
    accepted_supports = [
        r
        for r in rows
        if r.get("status") == "accepted" and r.get("relation", "supports") == "supports"
    ]
    if accepted_supports:
        return "sufficient"
    return "weak"


def assemble_explain_response(
    *,
    sentence: dict[str, Any],
    bound_objects: list[Any],
    relations: list[str],
    file_titles: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Build explain payload from already-authorized ORM rows + binding relations.

    Caller MUST load rows under tenant scope; this function does not invent ids.
    """
    file_titles = file_titles or {}
    evidence: list[dict[str, Any]] = []
    chain: list[dict[str, str]] = []
    for row, relation in zip(bound_objects, relations):
        file_id = getattr(row, "file_id", None)
        dto = serialize_evidence_object(
            row,
            relation=relation,
            file_title=file_titles.get(file_id) if file_id is not None else None,
        )
        evidence.append(dto)
        chain.append(
            {
                "step": "binding",
                "detail": (
                    f"anchor {sentence.get('block_id') or sentence.get('range_start')} "
                    f"→ evidence {dto.get('id')} ({relation})"
                ),
            }
        )
        prov = dto.get("provenance") or {}
        if prov.get("pipeline_version") or dto.get("study_quality"):
            chain.append(
                {
                    "step": "provenance",
                    "detail": (
                        f"pipeline {prov.get('pipeline_version') or dto.get('pipeline_version')}; "
                        f"study_quality {dto.get('study_quality') or 'n/a'}; "
                        f"confidence_band {dto.get('confidence_band')}"
                    ),
                }
            )

    # Stable server order: accepted first, then band, then id
    band_rank = {"high": 0, "moderate": 1, "low": 2}
    status_rank = {"accepted": 0, "candidate": 1, "rejected": 2, "superseded": 3}
    evidence.sort(
        key=lambda e: (
            status_rank.get(str(e.get("status")), 9),
            band_rank.get(str(e.get("confidence_band")), 9),
            e.get("id") or 0,
        )
    )

    return {
        "status": "ok",
        "sufficiency": compute_sufficiency(evidence),
        "sentence": sentence,
        "evidence": evidence,
        "chain": chain,
        "warnings": [],
    }
