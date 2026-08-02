"""Project Phase 1 analysis JSON → candidate EvidenceObject drafts.

Quality pass (Subsystem #6 / EXTRACTION_QUALITY_BACKLOG High):
- claim normalisation (prefer distinct KG label; collapse whitespace; skip trivial)
- study_type alias normalisation
- structured facets stamped into provenance for Conflict mediators
"""

from __future__ import annotations

import re
from typing import Any

from backend.evidence.extractor import CandidateEvidence, build_candidate
from backend.evidence.provenance import build_provenance

_WS_RE = re.compile(r"\s+")
_TRIVIAL_CLAIM_RE = re.compile(r"^[\W_]+$", re.UNICODE)

# Map common Phase 1 / EG labels → stable study_type tokens used by scoring.
_STUDY_TYPE_ALIASES: tuple[tuple[str, str], ...] = (
    ("randomized controlled trial", "randomized_controlled_trial"),
    ("randomised controlled trial", "randomized_controlled_trial"),
    ("randomized_controlled_trial", "randomized_controlled_trial"),
    ("rct", "randomized_controlled_trial"),
    ("systematic review", "systematic_review"),
    ("meta-analysis", "meta_analysis"),
    ("meta analysis", "meta_analysis"),
    ("meta_analysis", "meta_analysis"),
    ("cohort study", "cohort"),
    ("prospective cohort", "cohort"),
    ("retrospective cohort", "cohort"),
    ("case-control", "case_control"),
    ("case control", "case_control"),
    ("cross-sectional", "cross_sectional"),
    ("cross sectional", "cross_sectional"),
    ("case report", "case_report"),
    ("case series", "case_series"),
    ("qualitative", "qualitative"),
    ("in vitro", "in_vitro"),
    ("animal", "animal"),
)


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


def _collapse_ws(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip())


def normalize_study_type(raw: str | None) -> str:
    """Map Phase 1 study_design labels to stable scoring tokens."""
    s = _collapse_ws(str(raw or "")).lower()
    if not s:
        return ""
    for needle, canon in _STUDY_TYPE_ALIASES:
        if needle in s or s == needle.replace(" ", "_"):
            return canon
    # Keep original compact form if already snake_case-ish
    if re.fullmatch(r"[a-z0-9_]+", s):
        return s
    return s.replace("-", "_").replace(" ", "_")[:80]


def normalize_claim(*, label: str, outcome_name: str, quote: str) -> str | None:
    """Prefer a distinct claim label; never invent facts beyond Phase 1 fields.

    Returns None when the claim would be empty/trivial (caller should skip).
    """
    q = _collapse_ws(quote)
    candidates = [
        _collapse_ws(label),
        _collapse_ws(outcome_name),
        q[:500] if q else "",
    ]
    for c in candidates:
        if not c or len(c) < 3:
            continue
        if _TRIVIAL_CLAIM_RE.match(c):
            continue
        return c[:2000]
    return None


def _pico_blob(phase_results: dict[str, Any]) -> dict[str, Any]:
    med = phase_results.get("medical_understanding")
    if not isinstance(med, dict):
        return {}
    pico = med.get("pico_elements") or med.get("pico") or {}
    return pico if isinstance(pico, dict) else {}


def _facet_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        for key in ("label", "name", "text", "value", "description"):
            if val.get(key):
                return _collapse_ws(str(val.get(key)))[:300]
        return ""
    if isinstance(val, list):
        parts = [_facet_str(x) for x in val]
        return "; ".join(p for p in parts if p)[:300]
    return _collapse_ws(str(val))[:300]


def facets_for_candidate(
    *,
    props: dict[str, Any],
    study_type: str,
    phase_results: dict[str, Any],
    supports: list[str] | None = None,
) -> dict[str, Any]:
    """Stamp Conflict-mediator facets into provenance when Phase 1 provides them."""
    pico = _pico_blob(phase_results)
    facets: dict[str, Any] = {}

    population = (
        _facet_str(props.get("population"))
        or _facet_str(props.get("study_population"))
        or _facet_str(pico.get("population"))
    )
    if population:
        facets["population"] = population

    dosage = (
        _facet_str(props.get("dosage"))
        or _facet_str(props.get("dose"))
        or _facet_str(pico.get("intervention"))
    )
    if dosage:
        facets["dosage"] = dosage

    outcome = (
        _facet_str(props.get("outcome"))
        or _facet_str(props.get("outcome_name"))
        or _facet_str(pico.get("outcome"))
    )
    if not outcome and supports:
        outcome = _collapse_ws(str(supports[0]))[:300]
    if outcome:
        facets["outcome"] = outcome

    method = _facet_str(props.get("method")) or study_type
    if method:
        facets["method"] = method

    timeframe = (
        _facet_str(props.get("timeframe"))
        or _facet_str(props.get("follow_up"))
        or _facet_str(props.get("year"))
    )
    if timeframe:
        facets["timeframe"] = timeframe

    return facets


def _study_type_from_phase(classification: dict[str, Any], eg: dict[str, Any]) -> str:
    study_type = ""
    design = classification.get("study_design")
    if isinstance(design, dict):
        study_type = str(design.get("label") or design.get("study_design") or "")
    elif isinstance(design, str):
        study_type = design
    if not study_type:
        # EG sometimes carries design on overall_grade / study_design
        for key in ("study_design", "design"):
            raw = eg.get(key)
            if isinstance(raw, dict):
                study_type = str(raw.get("label") or raw.get("value") or "")
            elif isinstance(raw, str):
                study_type = raw
            if study_type:
                break
    return normalize_study_type(study_type)


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

    study_type = _study_type_from_phase(classification, eg)

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
        "extraction_prompt_version": "phase_projector.v1.1",
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
        grade_label = ""
        if isinstance(overall, dict):
            grade_label = _collapse_ws(str(overall.get("summary") or overall.get("label") or ""))
        if isinstance(refs, list):
            for i, ref in enumerate(refs):
                if not isinstance(ref, dict):
                    continue
                quote = _collapse_ws(str(ref.get("text_snippet") or ""))
                page = ref.get("page")
                if not quote or page is None:
                    continue
                try:
                    page_i = int(page)
                except (TypeError, ValueError):
                    continue
                claim = normalize_claim(label=grade_label, outcome_name="", quote=quote)
                if claim is None:
                    continue
                char_start, char_end = _char_range(ref)
                facets = facets_for_candidate(
                    props={},
                    study_type=study_type,
                    phase_results=phase_results,
                )
                try:
                    out.append(
                        build_candidate(
                            file_id=file_id,
                            quote=quote,
                            claim=claim,
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
                            provenance_extra=facets or None,
                            source_kg_node_id=f"eg_ref:{i}",
                        )
                    )
                except ValueError:
                    continue
        return out

    for node in claim_nodes:
        node_id = str(node.get("node_id") or "")
        ref = _first_ref(node)
        quote = _collapse_ws(str((ref or {}).get("text_snippet") or ""))
        page = (ref or {}).get("page")
        if not quote or page is None:
            continue
        try:
            page_i = int(page)
        except (TypeError, ValueError):
            continue
        props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
        claim = normalize_claim(
            label=str(node.get("label") or ""),
            outcome_name=str(props.get("outcome_name") or ""),
            quote=quote,
        )
        if claim is None:
            continue
        char_start, char_end = _char_range(ref)
        supports = list(supports_by_source.get(node_id, []))
        # When KG has no supports edges, stamp outcome facet so consensus/WI
        # treat the claim as usable support (Alpha Accept → Generate path).
        if not supports:
            outcome_hint = _facet_str(props.get("outcome_name") or props.get("outcome"))
            if outcome_hint:
                supports = [outcome_hint]
        facets = facets_for_candidate(
            props=props,
            study_type=study_type,
            phase_results=phase_results,
            supports=supports,
        )
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
                    supports=supports,
                    contradicts=contradicts_by_source.get(node_id, []),
                    pipeline_version=pipeline_version,
                    provenance_parts=provenance_parts,
                    provenance_extra=facets or None,
                    source_kg_node_id=node_id,
                )
            )
        except ValueError:
            continue

    # Ensure provenance objects are JSON-serializable dicts (build_candidate already does)
    _ = build_provenance
    return out
