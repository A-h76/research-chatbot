"""Evidence Consensus stage (Phase 2.3 Sprint 3).

Aggregates ranked EvidenceObjects into supporting / contradicting / neutral.
No LLM — pure counts + ordinal label. Never invents or mutates objects.
"""

from __future__ import annotations

from typing import Any, Literal

CONSENSUS_VERSION = "1.0.0"

Stance = Literal["supporting", "contradicting", "neutral"]
ConsensusLabel = Literal["strong", "moderate", "contested", "opposed", "none"]


def classify_stance(
    obj: dict[str, Any],
    *,
    binding_relation: str | None = None,
) -> Stance:
    """Map one EvidenceObject to a consensus bucket.

    Preference order:
    1. Binding / explicit relation (supports|contradicts|related)
    2. Non-empty contradicts / supports arrays on the object
    3. Neutral
    """
    rel = (binding_relation or obj.get("relation") or "").strip().lower()
    if rel == "supports":
        return "supporting"
    if rel == "contradicts":
        return "contradicting"
    if rel == "related":
        return "neutral"

    supports = obj.get("supports") or []
    contradicts = obj.get("contradicts") or []
    n_sup = len(supports) if isinstance(supports, list) else 0
    n_con = len(contradicts) if isinstance(contradicts, list) else 0

    if n_con > 0 and n_sup == 0:
        return "contradicting"
    if n_sup > 0 and n_con == 0:
        return "supporting"
    if n_sup > 0 and n_con > 0:
        # Contested object surface — count toward contradicting for safety
        return "contradicting" if n_con >= n_sup else "supporting"
    return "neutral"


def consensus_label(*, supporting: int, contradicting: int, neutral: int = 0) -> ConsensusLabel:
    """Ordinal consensus from bucket counts (ADD-0005 Month 4 shape)."""
    _ = neutral  # retained for API symmetry; does not drive label
    if supporting == 0 and contradicting == 0:
        return "none"
    if supporting == 0 and contradicting > 0:
        return "opposed"
    if contradicting >= supporting:
        return "contested"
    # supporting > contradicting — strong when clearly dominant (e.g. 8 vs 2)
    if supporting >= 2 and supporting >= 2 * contradicting:
        return "strong"
    return "moderate"


def aggregate_consensus(
    objects: list[dict[str, Any]],
    *,
    binding_relations: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Aggregate EvidenceObjects into structured consensus. Same object ids only."""
    binding_relations = binding_relations or {}
    supporting_ids: list[int] = []
    contradicting_ids: list[int] = []
    neutral_ids: list[int] = []

    for obj in objects:
        oid = int(obj.get("id") or 0)
        if not oid:
            continue
        stance = classify_stance(obj, binding_relation=binding_relations.get(oid))
        if stance == "supporting":
            supporting_ids.append(oid)
        elif stance == "contradicting":
            contradicting_ids.append(oid)
        else:
            neutral_ids.append(oid)

    supporting = len(supporting_ids)
    contradicting = len(contradicting_ids)
    neutral = len(neutral_ids)
    label = consensus_label(
        supporting=supporting, contradicting=contradicting, neutral=neutral
    )

    return {
        "label": label,
        "supporting": supporting,
        "contradicting": contradicting,
        "neutral": neutral,
        "supporting_ids": supporting_ids,
        "contradicting_ids": contradicting_ids,
        "neutral_ids": neutral_ids,
    }


def apply_consensus_stage(
    ranking_result: dict[str, Any],
    *,
    binding_relations: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Compose Consensus on a Ranking-stage envelope."""
    objects = list(ranking_result.get("objects") or [])
    consensus = aggregate_consensus(objects, binding_relations=binding_relations)
    return {
        "query": ranking_result.get("query") or {},
        "objects": objects,
        "total": ranking_result.get("total", len(objects)),
        "truncated": bool(ranking_result.get("truncated")),
        "stage": "consensus",
        "consensus_version": CONSENSUS_VERSION,
        "consensus": consensus,
        "ranking_version": ranking_result.get("ranking_version"),
        "ranking_strategy": ranking_result.get("ranking_strategy"),
        "retrieval_version": ranking_result.get("retrieval_version"),
    }
