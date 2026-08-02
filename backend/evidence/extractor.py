"""Evidence extraction entrypoints (Research Ready → candidate EvidenceObjects).

Full worker wiring lands in BE-C. This module defines the public contract and
validation helpers used by unit tests and the future handler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .objects import require_page_anchor
from .provenance import build_provenance, compute_content_hash, compute_input_content_hash
from .scoring import confidence_band_from_grades

PIPELINE_VERSION_DEFAULT = "2.2.0"


@dataclass(frozen=True)
class CandidateEvidence:
    file_id: int
    page: int | None
    char_start: int | None
    char_end: int | None
    section: str
    quote: str
    claim: str
    study_type: str
    study_quality: str
    supports: list[Any]
    contradicts: list[Any]
    limitations: list[Any]
    confidence_band: str
    content_hash: str
    provenance: dict[str, Any]
    source_kg_node_id: str = ""


def build_candidate(
    *,
    file_id: int,
    quote: str,
    claim: str,
    page: int | None = None,
    char_start: int | None = None,
    char_end: int | None = None,
    section: str = "",
    study_type: str = "",
    study_quality: str = "",
    risk_of_bias: str = "",
    consistency: str = "",
    has_contradiction: bool = False,
    supports: list[Any] | None = None,
    contradicts: list[Any] | None = None,
    limitations: list[Any] | None = None,
    pipeline_version: str = PIPELINE_VERSION_DEFAULT,
    provenance_parts: dict[str, Any] | None = None,
    provenance_extra: dict[str, Any] | None = None,
    source_kg_node_id: str = "",
    require_page: bool = True,
) -> CandidateEvidence:
    require_page_anchor(file_id=file_id, quote=quote, page=page)
    if require_page and page is None:
        raise ValueError("page-anchored evidence required; skip ungrounded candidate")
    q = (quote or "").strip()
    c = (claim or "").strip()
    if not q:
        raise ValueError("empty quote; skip candidate")
    if not c or len(c) < 3:
        raise ValueError("empty or trivial claim; skip candidate")
    band = confidence_band_from_grades(
        study_type=study_type,
        study_quality=study_quality,
        risk_of_bias=risk_of_bias,
        consistency=consistency,
        has_contradiction=has_contradiction,
    )
    parts = provenance_parts or {}
    extra = dict(provenance_extra or {})
    # Surface weak-claim signal for Inspector / Conflict without changing DTO schema.
    if c.lower() == q.lower():
        extra.setdefault("claim_equals_quote", True)
    provenance = build_provenance(
        pipeline_version=pipeline_version,
        document_understanding=parts.get("document_understanding", ""),
        evidence_grading=parts.get("evidence_grading", ""),
        knowledge_graph=parts.get("knowledge_graph", ""),
        extraction_prompt_version=parts.get("extraction_prompt_version", ""),
        extra=extra or None,
    )
    return CandidateEvidence(
        file_id=file_id,
        page=page,
        char_start=char_start,
        char_end=char_end,
        section=section or "",
        quote=q,
        claim=c,
        study_type=study_type or "",
        study_quality=study_quality or "",
        supports=list(supports or []),
        contradicts=list(contradicts or []),
        limitations=list(limitations or []),
        confidence_band=band,
        content_hash=compute_content_hash(
            file_id=file_id,
            page=page,
            char_start=char_start,
            char_end=char_end,
            quote=q,
            claim=c,
        ),
        provenance=provenance,
        source_kg_node_id=source_kg_node_id or "",
    )


def run_extraction_plan(
    *,
    is_research_ready: bool,
    file_fingerprint: str,
    pipeline_version: str = PIPELINE_VERSION_DEFAULT,
    force: bool = False,
    prior_run_succeeded: bool = False,
    prior_input_hash: str | None = None,
    build_candidates: Callable[[], list[CandidateEvidence]],
) -> dict[str, Any]:
    """Pure control-flow for extract idempotency / gating (no DB)."""
    if not is_research_ready:
        return {"status": "skipped", "reason": "not_research_ready", "objects_created": 0}

    input_hash = compute_input_content_hash(
        file_fingerprint=file_fingerprint,
        pipeline_version=pipeline_version,
    )
    if prior_run_succeeded and not force and prior_input_hash == input_hash:
        return {
            "status": "succeeded",
            "reason": "idempotent_reuse",
            "objects_created": 0,
            "input_content_hash": input_hash,
        }

    candidates = build_candidates()
    return {
        "status": "succeeded",
        "reason": "extracted",
        "objects_created": len(candidates),
        "input_content_hash": input_hash,
        "candidates": candidates,
    }
