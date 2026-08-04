"""Project Phase 1 analysis JSON → candidate EvidenceObject drafts.

Quality pass (Subsystem #6 / EXTRACTION_QUALITY_BACKLOG High) + Paper Analysis 2.4:
- claim normalisation (prefer distinct KG label; collapse whitespace; skip trivial)
- study_type alias normalisation
- structured facets stamped into provenance for Conflict mediators
- enrich method/confidence/limitations from DU profiles + EG when present
- per-file candidate cap (noise control)
"""

from __future__ import annotations

import re
from typing import Any

from backend.evidence.extractor import CandidateEvidence, build_candidate
from backend.evidence.provenance import build_provenance

# Bump when projector facet / ranking rules change (must match extract hash).
EXTRACTION_PROMPT_VERSION = "phase_projector.v1.2"
MAX_CANDIDATES_PER_FILE = 30

_WS_RE = re.compile(r"\s+")
_TRIVIAL_CLAIM_RE = re.compile(r"^[\W_]+$", re.UNICODE)
_BAND_RANK = {"high": 0, "medium": 1, "low": 2, "unknown": 3, "": 4}

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


def _du_blob(phase_results: dict[str, Any]) -> dict[str, Any]:
    du = phase_results.get("document_understanding")
    return du if isinstance(du, dict) else {}


def _methodology_profile(phase_results: dict[str, Any]) -> dict[str, Any]:
    du = _du_blob(phase_results)
    mp = du.get("methodology_profile")
    return mp if isinstance(mp, dict) else {}


def _statistics_profile(phase_results: dict[str, Any]) -> dict[str, Any]:
    du = _du_blob(phase_results)
    sp = du.get("statistics_profile")
    return sp if isinstance(sp, dict) else {}


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


def _profile_field_text(profile: dict[str, Any], key: str) -> str:
    return _facet_str(profile.get(key))


def facets_for_candidate(
    *,
    props: dict[str, Any],
    study_type: str,
    phase_results: dict[str, Any],
    supports: list[str] | None = None,
    confidence_band: str = "",
    quote: str = "",
) -> dict[str, Any]:
    """Stamp Conflict-mediator facets into provenance when Phase 1 provides them."""
    pico = _pico_blob(phase_results)
    methodology = _methodology_profile(phase_results)
    statistics = _statistics_profile(phase_results)
    facets: dict[str, Any] = {}

    population = (
        _facet_str(props.get("population"))
        or _facet_str(props.get("study_population"))
        or _facet_str(pico.get("population"))
        or _profile_field_text(methodology, "population")
    )
    if population:
        facets["population"] = population

    dosage = (
        _facet_str(props.get("dosage"))
        or _facet_str(props.get("dose"))
        or _facet_str(pico.get("intervention"))
        or _profile_field_text(methodology, "intervention")
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

    method = (
        _facet_str(props.get("method"))
        or _profile_field_text(methodology, "study_design")
        or study_type
    )
    if method:
        facets["method"] = method

    timeframe = (
        _facet_str(props.get("timeframe"))
        or _facet_str(props.get("follow_up"))
        or _facet_str(props.get("year"))
    )
    if timeframe:
        facets["timeframe"] = timeframe

    sample_size = _profile_field_text(methodology, "sample_size")
    if sample_size:
        facets["sample_size"] = sample_size

    dataset = _profile_field_text(methodology, "dataset")
    if dataset:
        facets["dataset"] = dataset

    if confidence_band:
        facets["confidence"] = confidence_band

    q = _collapse_ws(quote)
    if q:
        facets["quote"] = q[:400]

    if statistics.get("has_content"):
        stat_bits: list[str] = []
        for key, label in (
            ("tests", "test"),
            ("p_values", "p"),
            ("effect_sizes", "effect"),
        ):
            items = statistics.get(key) or []
            if not isinstance(items, list):
                continue
            for item in items[:2]:
                text = _facet_str(item)
                if text:
                    stat_bits.append(f"{label}: {text}")
        if stat_bits:
            facets["statistical_signals"] = "; ".join(stat_bits)[:400]

    return facets


def limitations_for_candidate(
    *,
    props: dict[str, Any],
    phase_results: dict[str, Any],
    eg: dict[str, Any],
) -> list[str]:
    """Author-stated / Phase-1 limitations only — never invent critique."""
    out: list[str] = []
    seen: set[str] = set()

    def _add(raw: Any) -> None:
        text = _facet_str(raw)
        if not text or len(text) < 8:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(text[:400])

    for key in ("limitations", "limitation", "threats_to_validity"):
        val = props.get(key)
        if isinstance(val, list):
            for item in val:
                _add(item)
        else:
            _add(val)

    rob = eg.get("risk_of_bias")
    if isinstance(rob, dict):
        for key in ("summary", "rationale", "notes", "limitations"):
            _add(rob.get(key))
        domains = rob.get("domains")
        if isinstance(domains, list):
            for d in domains[:3]:
                if isinstance(d, dict) and str(d.get("judgment") or "").lower() in {
                    "high",
                    "serious",
                    "critical",
                }:
                    label = _facet_str(d.get("domain") or d.get("name") or d.get("label"))
                    note = _facet_str(d.get("rationale") or d.get("notes"))
                    if label and note:
                        _add(f"{label}: {note}")
                    elif label:
                        _add(f"Risk of bias — {label}")

    overall = eg.get("overall_grade")
    if isinstance(overall, dict):
        _add(overall.get("limitations"))

    # Paper Analysis 2.5 — author-stated limitations profile on DU.
    du = phase_results.get("document_understanding")
    if isinstance(du, dict):
        profile = du.get("limitations_novelty_profile")
        if isinstance(profile, dict):
            for item in profile.get("limitations") or []:
                if isinstance(item, dict) and item.get("author_stated") is not False:
                    _add(item.get("text"))
                else:
                    _add(item)

    return out[:6]


def _study_type_from_phase(
    classification: dict[str, Any], eg: dict[str, Any], phase_results: dict[str, Any]
) -> str:
    study_type = ""
    design = classification.get("study_design")
    if isinstance(design, dict):
        study_type = str(design.get("label") or design.get("study_design") or "")
    elif isinstance(design, str):
        study_type = design
    if not study_type:
        for key in ("study_design", "design"):
            raw = eg.get(key)
            if isinstance(raw, dict):
                study_type = str(raw.get("label") or raw.get("value") or "")
            elif isinstance(raw, str):
                study_type = raw
            if study_type:
                break
    if not study_type:
        study_type = _profile_field_text(_methodology_profile(phase_results), "study_design")
    return normalize_study_type(study_type)


def _dedupe_candidates(cands: list[CandidateEvidence]) -> list[CandidateEvidence]:
    out: list[CandidateEvidence] = []
    seen: set[str] = set()
    for c in cands:
        key = f"{(c.claim or '').strip().lower()}|{c.page}"
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _cap_candidates(
    cands: list[CandidateEvidence], *, limit: int = MAX_CANDIDATES_PER_FILE
) -> list[CandidateEvidence]:
    """Deduplicate by claim+page and keep highest-signal candidates."""
    ranked = sorted(
        cands,
        key=lambda c: (
            _BAND_RANK.get(str(c.confidence_band or "").lower(), 4),
            0 if c.supports else 1,
            0 if c.page is not None else 1,
            -len(c.quote or ""),
        ),
    )
    return _dedupe_candidates(ranked)[: max(0, int(limit))]


def _append_candidate(
    out: list[CandidateEvidence],
    *,
    file_id: int,
    quote: str,
    claim: str,
    page_i: int,
    char_start: int | None,
    char_end: int | None,
    section: str,
    study_type: str,
    study_quality: str,
    rob: str,
    consistency: str,
    has_contradiction: bool,
    supports: list[str] | None,
    contradicts: list[str] | None,
    limitations: list[str],
    pipeline_version: str,
    provenance_parts: dict[str, Any],
    props: dict[str, Any],
    phase_results: dict[str, Any],
    source_kg_node_id: str,
) -> None:
    try:
        provisional = build_candidate(
            file_id=file_id,
            quote=quote,
            claim=claim,
            page=page_i,
            char_start=char_start,
            char_end=char_end,
            section=section,
            study_type=study_type,
            study_quality=study_quality,
            risk_of_bias=rob,
            consistency=consistency,
            has_contradiction=has_contradiction,
            supports=supports,
            contradicts=contradicts,
            limitations=limitations,
            pipeline_version=pipeline_version,
            provenance_parts=provenance_parts,
            provenance_extra=None,
            source_kg_node_id=source_kg_node_id,
        )
    except ValueError:
        return
    facets = facets_for_candidate(
        props=props,
        study_type=study_type,
        phase_results=phase_results,
        supports=supports,
        confidence_band=provisional.confidence_band,
        quote=quote,
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
                section=section,
                study_type=study_type,
                study_quality=study_quality,
                risk_of_bias=rob,
                consistency=consistency,
                has_contradiction=has_contradiction,
                supports=supports,
                contradicts=contradicts,
                limitations=limitations,
                pipeline_version=pipeline_version,
                provenance_parts=provenance_parts,
                provenance_extra=facets or None,
                source_kg_node_id=source_kg_node_id,
            )
        )
    except ValueError:
        return


def candidates_from_phase_results(
    *,
    file_id: int,
    phase_results: dict[str, Any],
    pipeline_version: str = "2.2.0",
    max_candidates: int = MAX_CANDIDATES_PER_FILE,
) -> list[CandidateEvidence]:
    """Map KG evidence_claim nodes (+ EG grades) into page-anchored candidates.

    Skips ungrounded claims (no page + quote). Never invents pages/quotes.
    Caps volume to reduce noise (Paper Analysis 2.4).
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

    study_type = _study_type_from_phase(classification, eg, phase_results)

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
        "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
    }

    out: list[CandidateEvidence] = []
    claim_nodes = [
        n
        for n in (kg.get("nodes") or [])
        if isinstance(n, dict) and str(n.get("node_type") or "").lower() in {"evidence_claim", "evidenceclaim"}
    ]

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
                limitations = limitations_for_candidate(props={}, phase_results=phase_results, eg=eg)
                _append_candidate(
                    out,
                    file_id=file_id,
                    quote=quote,
                    claim=claim,
                    page_i=page_i,
                    char_start=char_start,
                    char_end=char_end,
                    section=str(ref.get("section") or ""),
                    study_type=study_type,
                    study_quality=study_quality,
                    rob=rob,
                    consistency=consistency,
                    has_contradiction=has_contradiction,
                    supports=None,
                    contradicts=None,
                    limitations=limitations,
                    pipeline_version=pipeline_version,
                    provenance_parts=provenance_parts,
                    props={},
                    phase_results=phase_results,
                    source_kg_node_id=f"eg_ref:{i}",
                )
        return _cap_candidates(out, limit=max_candidates)

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
        if not supports:
            outcome_hint = _facet_str(props.get("outcome_name") or props.get("outcome"))
            if outcome_hint:
                supports = [outcome_hint]
        limitations = limitations_for_candidate(props=props, phase_results=phase_results, eg=eg)
        _append_candidate(
            out,
            file_id=file_id,
            quote=quote,
            claim=claim,
            page_i=page_i,
            char_start=char_start,
            char_end=char_end,
            section=str((ref or {}).get("section") or ""),
            study_type=study_type,
            study_quality=study_quality or str(props.get("grade_value") or ""),
            rob=rob,
            consistency=consistency,
            has_contradiction=has_contradiction or bool(contradicts_by_source.get(node_id)),
            supports=supports,
            contradicts=contradicts_by_source.get(node_id, []),
            limitations=limitations,
            pipeline_version=pipeline_version,
            provenance_parts=provenance_parts,
            props=props,
            phase_results=phase_results,
            source_kg_node_id=node_id,
        )

    _ = build_provenance
    return _cap_candidates(out, limit=max_candidates)
