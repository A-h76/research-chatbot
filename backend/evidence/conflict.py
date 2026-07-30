"""Evidence Conflict stage (Phase 2.3 Sprint 4).

Codes conflict mediators between supporting and contradicting EvidenceObjects.
No LLM — structured metadata + lexical facets only. Links object ids; never invents.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from backend.evidence.consensus import aggregate_consensus, classify_stance

CONFLICT_VERSION = "1.2.0"

Mediator = Literal[
    "population_differs",
    "dosage_differs",
    "method_differs",
    "outcome_differs",
    "timeframe_differs",
    "statistics_differs",
]

MEDIATOR_ORDER: tuple[Mediator, ...] = (
    "population_differs",
    "dosage_differs",
    "method_differs",
    "outcome_differs",
    "timeframe_differs",
    "statistics_differs",
)

# Researcher-facing WHY copy (RI-004) — codes stay machine-stable.
MEDIATOR_WHY: dict[str, dict[str, str]] = {
    "population_differs": {
        "title": "Sample / population",
        "why": "Studies may disagree because they enroll different populations.",
    },
    "dosage_differs": {
        "title": "Dosage / regimen",
        "why": "Studies may disagree because dose or regimen differs.",
    },
    "method_differs": {
        "title": "Methodology",
        "why": "Studies may disagree because study design or methods differ.",
    },
    "outcome_differs": {
        "title": "Outcome",
        "why": "Studies may disagree because they measure different outcomes.",
    },
    "timeframe_differs": {
        "title": "Timeframe",
        "why": "Studies may disagree because follow-up length or era differs.",
    },
    "statistics_differs": {
        "title": "Statistics",
        "why": "Studies may disagree because statistical approaches or reported effects differ.",
    },
}

_POPULATION_RE = re.compile(
    r"\b("
    r"adults?|children|pediatric|paediatric|adolescents?|elderly|older\s+adults?|"
    r"women|men|pregnant|pregnancy|neonates?|infants?|"
    r"type\s*2|type\s*1|t2dm|t1dm|obesity|obese|"
    r"asian|european|african|hispanic|"
    r"n\s*=\s*\d+"
    r")\b",
    re.I,
)
_DOSAGE_RE = re.compile(
    r"\b("
    r"\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ug|g|ml|iu)\b|"
    r"once\s+daily|twice\s+daily|bid|tid|qid|"
    r"high[\s-]?dose|low[\s-]?dose|dose|dosage|titrat(?:e|ion)"
    r")\b",
    re.I,
)
_TIMEFRAME_RE = re.compile(
    r"\b("
    r"(?:19|20)\d{2}|"
    r"\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?)|"
    r"short[\s-]?term|long[\s-]?term|follow[\s-]?up"
    r")\b",
    re.I,
)
_STATISTICS_RE = re.compile(
    r"\b("
    r"p\s*[<=>]\s*0?\.\d+|p-?value|confidence interval|\bci\b|"
    r"odds ratio|\bor\b|hazard ratio|\bhr\b|relative risk|\brr\b|"
    r"cohen'?s?\s*d|effect size|anova|regression|intention[\s-]?to[\s-]?treat|\bitt\b|"
    r"n\s*=\s*\d+|sample size"
    r")\b",
    re.I,
)
_METHOD_NORMALIZE = re.compile(r"[^a-z0-9]+")


def _norm_method(study_type: Any) -> str:
    text = _METHOD_NORMALIZE.sub(" ", str(study_type or "").strip().lower()).strip()
    return text


def _text_blob(obj: dict[str, Any]) -> str:
    parts: list[str] = [
        str(obj.get("claim") or ""),
        str(obj.get("quote") or ""),
        str(obj.get("section") or ""),
    ]
    for key in ("limitations", "supports", "contradicts"):
        val = obj.get(key) or []
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
        else:
            parts.append(str(val))
    prov = obj.get("provenance") or {}
    if isinstance(prov, dict):
        for key in (
            "population",
            "dosage",
            "method",
            "outcome",
            "study_population",
            "dose",
            "timeframe",
            "follow_up",
            "year",
        ):
            if prov.get(key) is not None:
                parts.append(str(prov.get(key)))
    return " ".join(parts)


def extract_facets(obj: dict[str, Any]) -> dict[str, set[str]]:
    """Pull comparable structured facets from an EvidenceObject DTO."""
    blob = _text_blob(obj)
    population = {m.group(0).lower() for m in _POPULATION_RE.finditer(blob)}
    dosage = {m.group(0).lower().replace("  ", " ") for m in _DOSAGE_RE.finditer(blob)}
    timeframe = {m.group(0).lower().replace("  ", " ") for m in _TIMEFRAME_RE.finditer(blob)}
    statistics = {m.group(0).lower().replace("  ", " ") for m in _STATISTICS_RE.finditer(blob)}

    method: set[str] = set()
    m = _norm_method(obj.get("study_type"))
    if m:
        method.add(m)
    # provenance override
    prov = obj.get("provenance") if isinstance(obj.get("provenance"), dict) else {}
    if prov.get("method"):
        method.add(_norm_method(prov.get("method")))
    if prov.get("population"):
        population.add(str(prov.get("population")).strip().lower())
    if prov.get("dosage") or prov.get("dose"):
        dosage.add(str(prov.get("dosage") or prov.get("dose")).strip().lower())
    if prov.get("timeframe") or prov.get("follow_up") or prov.get("year"):
        timeframe.add(
            str(prov.get("timeframe") or prov.get("follow_up") or prov.get("year")).strip().lower()
        )
    if prov.get("statistics") or prov.get("analysis"):
        statistics.add(str(prov.get("statistics") or prov.get("analysis")).strip().lower())

    outcomes: set[str] = set()
    for key in ("supports", "contradicts"):
        val = obj.get(key) or []
        if isinstance(val, list):
            for item in val:
                label = str(item).strip().lower()
                if label:
                    outcomes.add(label)
    if prov.get("outcome"):
        outcomes.add(str(prov.get("outcome")).strip().lower())

    return {
        "population": population,
        "dosage": dosage,
        "method": method,
        "outcome": outcomes,
        "timeframe": timeframe,
        "statistics": statistics,
    }


def _sets_differ(a: set[str], b: set[str]) -> bool:
    """True when both sides have signals and they do not match."""
    if not a or not b:
        return False
    return a != b


def detect_mediators(a: dict[str, Any], b: dict[str, Any]) -> list[Mediator]:
    """Code mediators explaining disagreement between two EvidenceObjects."""
    fa = extract_facets(a)
    fb = extract_facets(b)
    found: list[Mediator] = []
    if _sets_differ(fa["population"], fb["population"]):
        found.append("population_differs")
    if _sets_differ(fa["dosage"], fb["dosage"]):
        found.append("dosage_differs")
    if _sets_differ(fa["method"], fb["method"]):
        found.append("method_differs")
    if _sets_differ(fa["outcome"], fb["outcome"]):
        found.append("outcome_differs")
    if _sets_differ(fa["timeframe"], fb["timeframe"]):
        found.append("timeframe_differs")
    if _sets_differ(fa["statistics"], fb["statistics"]):
        found.append("statistics_differs")
    return found


def _facet_pair_detail(fa: dict[str, set[str]], fb: dict[str, set[str]], key: str) -> dict[str, list[str]] | None:
    a_vals = sorted(fa.get(key) or [])
    b_vals = sorted(fb.get(key) or [])
    if not a_vals or not b_vals or a_vals == b_vals:
        return None
    return {"supporting": a_vals[:8], "contradicting": b_vals[:8]}


def explain_link_why(
    a: dict[str, Any],
    b: dict[str, Any],
    mediators: list[Mediator],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build RI-004 WHY cards + compact facet diffs for one conflict pair."""
    fa = extract_facets(a)
    fb = extract_facets(b)
    facet_key = {
        "population_differs": "population",
        "dosage_differs": "dosage",
        "method_differs": "method",
        "outcome_differs": "outcome",
        "timeframe_differs": "timeframe",
        "statistics_differs": "statistics",
    }
    why_cards: list[dict[str, Any]] = []
    facet_detail: dict[str, Any] = {}
    for code in mediators:
        meta = MEDIATOR_WHY.get(code) or {"title": code, "why": "Studies disagree for an uncoded reason."}
        key = facet_key.get(code)
        detail = _facet_pair_detail(fa, fb, key) if key else None
        card = {
            "code": code,
            "title": meta["title"],
            "why": meta["why"],
        }
        if detail:
            card["supporting_signals"] = detail["supporting"]
            card["contradicting_signals"] = detail["contradicting"]
            facet_detail[key] = detail
        why_cards.append(card)
    return why_cards, facet_detail


def analyze_conflicts(
    objects: list[dict[str, Any]],
    *,
    binding_relations: dict[int, str] | None = None,
    max_links: int = 50,
) -> dict[str, Any]:
    """Link supporting vs contradicting objects with coded mediators."""
    binding_relations = binding_relations or {}
    by_id = {int(o["id"]): o for o in objects if o.get("id") is not None}

    supporting_ids: list[int] = []
    contradicting_ids: list[int] = []
    for obj in objects:
        oid = int(obj.get("id") or 0)
        if not oid:
            continue
        stance = classify_stance(obj, binding_relation=binding_relations.get(oid))
        if stance == "supporting":
            supporting_ids.append(oid)
        elif stance == "contradicting":
            contradicting_ids.append(oid)

    has_conflict = bool(supporting_ids) and bool(contradicting_ids)
    links: list[dict[str, Any]] = []
    mediator_set: set[Mediator] = set()
    mediated_pair_count = 0
    unexplained_pair_count = 0

    if has_conflict:
        for sid in supporting_ids:
            for cid in contradicting_ids:
                if len(links) >= max_links:
                    break
                a = by_id.get(sid)
                b = by_id.get(cid)
                if not a or not b:
                    continue
                mediators = detect_mediators(a, b)
                for m in mediators:
                    mediator_set.add(m)
                if mediators:
                    mediated_pair_count += 1
                else:
                    unexplained_pair_count += 1
                why_cards, facet_detail = explain_link_why(a, b, mediators)
                links.append(
                    {
                        "a_id": sid,
                        "b_id": cid,
                        "a_stance": "supporting",
                        "b_stance": "contradicting",
                        "mediators": mediators,
                        # Additive RI-004
                        "why": why_cards,
                        "facet_detail": facet_detail,
                        "unexplained": not bool(mediators),
                    }
                )
            if len(links) >= max_links:
                break

    ordered = [m for m in MEDIATOR_ORDER if m in mediator_set]
    pair_count = len(links)
    mediator_explanations = [
        {
            "code": m,
            "title": (MEDIATOR_WHY.get(m) or {}).get("title", m),
            "why": (MEDIATOR_WHY.get(m) or {}).get("why", ""),
        }
        for m in ordered
    ]
    return {
        "has_conflict": has_conflict,
        "mediators": ordered,
        "mediator_explanations": mediator_explanations,
        "links": links,
        "pair_count": pair_count,
        "supporting_ids": supporting_ids,
        "contradicting_ids": contradicting_ids,
        # Additive (A-403 / RI-004)
        "metrics": {
            "mediated_pair_count": mediated_pair_count,
            "unexplained_pair_count": unexplained_pair_count,
            "mediation_coverage": (
                round(mediated_pair_count / pair_count, 4) if pair_count else None
            ),
        },
        "product_summary": (
            None
            if not has_conflict
            else (
                f"{pair_count} supporting↔contradicting pair(s); "
                f"{mediated_pair_count} with coded WHY; "
                f"{unexplained_pair_count} unexplained."
            )
        ),
    }


def apply_conflict_stage(
    consensus_result: dict[str, Any],
    *,
    binding_relations: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Compose Conflict on a Consensus-stage envelope."""
    objects = list(consensus_result.get("objects") or [])
    # Prefer consensus buckets when present (same ids); recompute links from objects
    conflict = analyze_conflicts(objects, binding_relations=binding_relations)
    consensus = consensus_result.get("consensus")
    if consensus is None:
        consensus = aggregate_consensus(objects, binding_relations=binding_relations)

    return {
        "query": consensus_result.get("query") or {},
        "objects": objects,
        "total": consensus_result.get("total", len(objects)),
        "truncated": bool(consensus_result.get("truncated")),
        "stage": "conflict",
        "conflict_version": CONFLICT_VERSION,
        "conflict": conflict,
        "consensus": consensus,
        "consensus_version": consensus_result.get("consensus_version"),
        "ranking_version": consensus_result.get("ranking_version"),
        "ranking_strategy": consensus_result.get("ranking_strategy"),
        "ranking_diagnostics": consensus_result.get("ranking_diagnostics"),
        "retrieval_version": consensus_result.get("retrieval_version"),
    }
