"""Evidence Conflict stage (Phase 2.3 Sprint 4).

Codes conflict mediators between supporting and contradicting EvidenceObjects.
No LLM — structured metadata + lexical facets only. Links object ids; never invents.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from backend.evidence.consensus import aggregate_consensus, classify_stance

CONFLICT_VERSION = "1.0.0"

Mediator = Literal[
    "population_differs",
    "dosage_differs",
    "method_differs",
    "outcome_differs",
]

MEDIATOR_ORDER: tuple[Mediator, ...] = (
    "population_differs",
    "dosage_differs",
    "method_differs",
    "outcome_differs",
)

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
        for key in ("population", "dosage", "method", "outcome", "study_population", "dose"):
            if prov.get(key) is not None:
                parts.append(str(prov.get(key)))
    return " ".join(parts)


def extract_facets(obj: dict[str, Any]) -> dict[str, set[str]]:
    """Pull comparable structured facets from an EvidenceObject DTO."""
    blob = _text_blob(obj)
    population = {m.group(0).lower() for m in _POPULATION_RE.finditer(blob)}
    dosage = {m.group(0).lower().replace("  ", " ") for m in _DOSAGE_RE.finditer(blob)}

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
    return found


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
                links.append(
                    {
                        "a_id": sid,
                        "b_id": cid,
                        "a_stance": "supporting",
                        "b_stance": "contradicting",
                        "mediators": mediators,
                    }
                )
            if len(links) >= max_links:
                break

    ordered = [m for m in MEDIATOR_ORDER if m in mediator_set]
    return {
        "has_conflict": has_conflict,
        "mediators": ordered,
        "links": links,
        "pair_count": len(links),
        "supporting_ids": supporting_ids,
        "contradicting_ids": contradicting_ids,
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
        "retrieval_version": consensus_result.get("retrieval_version"),
    }
