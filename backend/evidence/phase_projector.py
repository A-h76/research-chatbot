"""Project Phase 1 analysis JSON → candidate EvidenceObject drafts."""

from __future__ import annotations

from typing import Any

from backend.evidence.extractor import CandidateEvidence, build_candidate
from backend.evidence.provenance import build_provenance


def _node_map(kg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(n.get("node_id")): n for n in (kg.get("nodes") or []) if isinstance(n, dict) and n.get("node_id")}


def _first_ref(node: dict[str, Any]) -> dict[str, Any] | None:
    refs = node.get("evidence_references") or []
    if isinstance(refs, list) and refs:
        ref = refs[0]
        return ref if isinstance(ref, dict) else None
    return None


def _char_range(ref: dict[str, Any] | None) -> tuple[int | None, int | None]:
    if not ref:
        return None, None
    cr = ref.get("character_range")
    if isinstance(cr, (list, tuple)) and len(cr) >= 2:
        try:
            return int(cr[0]), int(cr[1])
        except (TypeError, ValueError):
            return None, None
    return None, None


def candidates_from_phase_results(
    *,
    file_id: int,
    phase_results: dict[str, Any],
    pipeline_version: str = "2.2.0",
) -> list[CandidateEvidence]:
    """Map KG evidence_claim nodes (+ EG grades) into page-anchored candidates.

    Skips ungrounded claims (no page + quote). Never invents pages/quotes.
    """
    kg = phase_results.get("knowledge_graph") or {}
    eg = phase_results.get("evidence_grading") or {}
    classification = phase_results.get("classification") or {}

    if not isinstance(kg, dict):
        kg = {}
    if not isinstance(eg, dict):
        eg = {}
    if not isinstance(classification, dict):
        classification = {}

    study_quality = str(eg.get("study_quality") or "")
    if not study_quality:
        overall = eg.get("overall_grade") or {}
        if isinstance(overall, dict):
            study_quality = str(overall.get("grade_value") or "")

    rob = ""
    rob_obj = eg.get("risk_of_bias")
    if isinstance(rob_obj, dict):
        rob = str(rob_obj.get("overall_risk") or "")

    consistency = ""
    cons_obj = eg.get("consistency")
    if isinstance(cons_obj, dict):
        consistency = str(cons_obj.get("consistency_level") or "")

    study_type = ""
    design = classification.get("study_design")
    if isinstance(design, dict):
        study_type = str(design.get("label") or design.get("study_design") or "")
    elif isinstance(design, str):
        study_type = design

    nodes = _node_map(kg)
    edges = [e for e in (kg.get("edges") or []) if isinstance(e, dict)]

    supports_by_source: dict[str, list[str]] = {}
    contradicts_by_source: dict[str, list[str]] = {}
    has_contradiction = False
    for edge in edges:
        et = str(edge.get("edge_type") or "").lower()
        src = str(edge.get("source_node_id") or "")
        tgt = str(edge.get("target_node_id") or "")
        tgt_label = (nodes.get(tgt) or {}).get("label") or tgt
        if et == "supports" and src:
            supports_by_source.setdefault(src, []).append(str(tgt_label))
        elif et == "contradicts" and src:
            has_contradiction = True
            contradicts_by_source.setdefault(src, []).append(str(tgt_label))

    provenance_parts = {
        "document_understanding": "phase_results.document_understanding",
        "evidence_grading": str(eg.get("pipeline_version") or "evidence_grading"),
        "knowledge_graph": str(kg.get("pipeline_version") or kg.get("version") or "knowledge_graph"),
        "extraction_prompt_version": "phase_projector.v1",
    }

    out: list[CandidateEvidence] = []
    claim_nodes = [
        n
        for n in (kg.get("nodes") or [])
        if isinstance(n, dict) and str(n.get("node_type") or "").lower() in {"evidence_claim", "evidenceclaim"}
    ]

    # Fallback: EG overall_grade evidence references as weak candidates
    if not claim_nodes:
        overall = eg.get("overall_grade") if isinstance(eg.get("overall_grade"), dict) else {}
        refs = overall.get("evidence") if isinstance(overall, dict) else None
        if isinstance(refs, list):
            for i, ref in enumerate(refs):
                if not isinstance(ref, dict):
                    continue
                quote = str(ref.get("text_snippet") or "").strip()
                page = ref.get("page")
                if not quote or page is None:
                    continue
                try:
                    page_i = int(page)
                except (TypeError, ValueError):
                    continue
                char_start, char_end = _char_range(ref)
                try:
                    out.append(
                        build_candidate(
                            file_id=file_id,
                            quote=quote,
                            claim=quote[:500],
                            page=page_i,
                            char_start=char_start,
                            char_end=char_end,
                            section=str(ref.get("section") or ""),
                            study_type=study_type,
                            study_quality=study_quality,
                            risk_of_bias=rob,
                            consistency=consistency,
                            has_contradiction=has_contradiction,
                            pipeline_version=pipeline_version,
                            provenance_parts=provenance_parts,
                            source_kg_node_id=f"eg_ref:{i}",
                        )
                    )
                except ValueError:
                    continue
        return out

    for node in claim_nodes:
        node_id = str(node.get("node_id") or "")
        ref = _first_ref(node)
        quote = str((ref or {}).get("text_snippet") or "").strip()
        page = (ref or {}).get("page")
        if not quote or page is None:
            continue
        try:
            page_i = int(page)
        except (TypeError, ValueError):
            continue
        props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
        claim = str(node.get("label") or props.get("outcome_name") or quote)[:2000]
        char_start, char_end = _char_range(ref)
        try:
            out.append(
                build_candidate(
                    file_id=file_id,
                    quote=quote,
                    claim=claim,
                    page=page_i,
                    char_start=char_start,
                    char_end=char_end,
                    section=str((ref or {}).get("section") or ""),
                    study_type=study_type,
                    study_quality=study_quality or str(props.get("grade_value") or ""),
                    risk_of_bias=rob,
                    consistency=consistency,
                    has_contradiction=has_contradiction or bool(contradicts_by_source.get(node_id)),
                    supports=supports_by_source.get(node_id, []),
                    contradicts=contradicts_by_source.get(node_id, []),
                    pipeline_version=pipeline_version,
                    provenance_parts=provenance_parts,
                    source_kg_node_id=node_id,
                )
            )
        except ValueError:
            continue

    # Ensure provenance objects are JSON-serializable dicts (build_candidate already does)
    _ = build_provenance
    return out
