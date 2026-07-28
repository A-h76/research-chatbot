"""Evidence Reasoning stage (Phase 2.3 Sprint 5).

Builds a structured explanation chain from Retrieval → Ranking → Consensus → Conflict.
No LLM / no free-text generation — templated steps from coded pipeline outputs only.
Never invents EvidenceObjects.
"""

from __future__ import annotations

from typing import Any, Literal

REASONING_VERSION = "1.0.0"

SummaryCode = Literal[
    "insufficient",
    "opposed",
    "contested_with_mediators",
    "contested",
    "strong",
    "moderate",
    "none",
]

_MEDIATOR_LABELS = {
    "population_differs": "Population differs",
    "dosage_differs": "Dosage differs",
    "method_differs": "Method differs",
    "outcome_differs": "Outcome differs",
}

_CONSENSUS_TEMPLATES = {
    "none": "No supporting or contradicting EvidenceObjects in the ranked set.",
    "opposed": "Only contradicting EvidenceObjects; no supporting objects.",
    "contested": "Supporting and contradicting EvidenceObjects are balanced or contested.",
    "strong": "Supporting EvidenceObjects dominate contradicting ones.",
    "moderate": "Supporting EvidenceObjects outweigh contradicting ones, but not strongly.",
}


def _mediator_labels(mediators: list[str]) -> list[str]:
    return [_MEDIATOR_LABELS.get(m, m) for m in mediators]


def summary_code_from_stages(
    *,
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
    object_count: int,
) -> SummaryCode:
    if object_count <= 0:
        return "insufficient"
    label = (consensus or {}).get("label") or "none"
    has_conflict = bool((conflict or {}).get("has_conflict"))
    mediators = list((conflict or {}).get("mediators") or [])
    if label == "opposed":
        return "opposed"
    if label == "contested" and has_conflict and mediators:
        return "contested_with_mediators"
    if label == "contested":
        return "contested"
    if label == "strong":
        return "strong"
    if label == "moderate":
        return "moderate"
    if label == "none":
        return "none"
    return "insufficient"


def sufficiency_from_summary(code: SummaryCode) -> str:
    if code in {"strong", "moderate"}:
        return "sufficient"
    if code in {"contested", "contested_with_mediators", "opposed"}:
        return "weak"
    return "insufficient"


def build_reasoning_steps(
    *,
    query: dict[str, Any],
    objects: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
    ranking_strategy: str | None = None,
    total: int | None = None,
) -> list[dict[str, str]]:
    """Ordered coded steps — detail strings are templates, not model output."""
    steps: list[dict[str, str]] = []
    intent = (query or {}).get("intent") or ""
    n = len(objects)
    total_n = total if total is not None else n

    steps.append(
        {
            "step": "retrieval",
            "detail": f"intent={intent}; returned {n} of {total_n} EvidenceObject(s).",
        }
    )

    strategy = ranking_strategy or (query or {}).get("ranking_strategy") or "default_v0"
    top_ids = [int(o["id"]) for o in objects[:5] if o.get("id") is not None]
    steps.append(
        {
            "step": "ranking",
            "detail": f"strategy={strategy}; top_ids={top_ids}.",
        }
    )

    c = consensus or {}
    steps.append(
        {
            "step": "consensus",
            "detail": (
                f"label={c.get('label', 'none')}; "
                f"supporting={c.get('supporting', 0)}; "
                f"contradicting={c.get('contradicting', 0)}; "
                f"neutral={c.get('neutral', 0)}."
            ),
        }
    )

    cf = conflict or {}
    mediators = list(cf.get("mediators") or [])
    labels = _mediator_labels(mediators)
    if cf.get("has_conflict"):
        med_txt = ", ".join(labels) if labels else "uncoded (facets insufficient)"
        steps.append(
            {
                "step": "conflict",
                "detail": (
                    f"has_conflict=true; pair_count={cf.get('pair_count', 0)}; "
                    f"mediators={med_txt}."
                ),
            }
        )
    else:
        steps.append(
            {
                "step": "conflict",
                "detail": "has_conflict=false; no supporting×contradicting pairs.",
            }
        )

    code = summary_code_from_stages(consensus=c, conflict=cf, object_count=n)
    conclusion = _CONSENSUS_TEMPLATES.get(c.get("label") or "none", _CONSENSUS_TEMPLATES["none"])
    if code == "contested_with_mediators" and labels:
        conclusion = (
            f"{conclusion} Coded mediators: {', '.join(labels)}."
        )
    elif code == "insufficient":
        conclusion = "No EvidenceObjects available to reason over."
    steps.append({"step": "conclusion", "code": code, "detail": conclusion})

    return steps


def build_reasoning(
    *,
    query: dict[str, Any],
    objects: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
    ranking_strategy: str | None = None,
    total: int | None = None,
) -> dict[str, Any]:
    """Structured reasoning payload over existing EvidenceObject ids only."""
    evidence_ids = [int(o["id"]) for o in objects if o.get("id") is not None]
    code = summary_code_from_stages(
        consensus=consensus, conflict=conflict, object_count=len(objects)
    )
    steps = build_reasoning_steps(
        query=query,
        objects=objects,
        consensus=consensus,
        conflict=conflict,
        ranking_strategy=ranking_strategy,
        total=total,
    )
    return {
        "summary_code": code,
        "sufficiency": sufficiency_from_summary(code),
        "steps": steps,
        "evidence_ids": evidence_ids,
        "mediator_labels": _mediator_labels(list((conflict or {}).get("mediators") or [])),
    }


def apply_reasoning_stage(conflict_result: dict[str, Any]) -> dict[str, Any]:
    """Compose Reasoning on a Conflict-stage envelope."""
    objects = list(conflict_result.get("objects") or [])
    query = conflict_result.get("query") or {}
    reasoning = build_reasoning(
        query=query,
        objects=objects,
        consensus=conflict_result.get("consensus"),
        conflict=conflict_result.get("conflict"),
        ranking_strategy=conflict_result.get("ranking_strategy"),
        total=conflict_result.get("total"),
    )
    return {
        "query": query,
        "objects": objects,
        "total": conflict_result.get("total", len(objects)),
        "truncated": bool(conflict_result.get("truncated")),
        "stage": "reasoning",
        "reasoning_version": REASONING_VERSION,
        "reasoning": reasoning,
        "conflict": conflict_result.get("conflict"),
        "conflict_version": conflict_result.get("conflict_version"),
        "consensus": conflict_result.get("consensus"),
        "consensus_version": conflict_result.get("consensus_version"),
        "ranking_version": conflict_result.get("ranking_version"),
        "ranking_strategy": conflict_result.get("ranking_strategy"),
        "retrieval_version": conflict_result.get("retrieval_version"),
    }
