"""Evidence Consensus stage (Phase 2.3 Sprint 3 + A-403 metrics).

Aggregates ranked EvidenceObjects into supporting / contradicting / neutral.
No LLM — pure counts + ordinal label + additive metrics. Never invents or mutates objects.
"""

from __future__ import annotations

from typing import Any, Literal

CONSENSUS_VERSION = "1.2.0"

Stance = Literal["supporting", "contradicting", "neutral"]
ConsensusLabel = Literal["strong", "moderate", "contested", "opposed", "none"]
ProductConsensusLabel = Literal["Agree", "Disagree", "Mixed", "Weak evidence"]

_BAND_WEIGHT = {"high": 3.0, "moderate": 2.0, "low": 1.0}


def classify_stance(
    obj: dict[str, Any],
    *,
    binding_relation: str | None = None,
) -> Stance:
    """Map one EvidenceObject to a consensus bucket.

    Preference order:
    1. Binding / explicit relation (supports|contradicts|related)
    2. Non-empty contradicts / supports arrays on the object
    3. Claim-bearing object with no contradicts → supporting
       (extract often yields empty supports[] until KG edges exist;
       Alpha path Accept → Generate must not stall as all-neutral)
    4. Neutral
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

    claim = (obj.get("claim") or obj.get("quote") or "").strip()
    if claim:
        return "supporting"
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


def product_consensus_label(
    *,
    label: ConsensusLabel,
    supporting: int,
    contradicting: int,
    supporting_weight: float,
) -> ProductConsensusLabel:
    """Researcher-facing stance (RI-003). Keeps ordinal `label` frozen for clients."""
    if label == "opposed":
        return "Disagree"
    if label == "contested":
        return "Mixed"
    if label == "none":
        return "Weak evidence"
    # strong | moderate — require enough supporting mass to call Agree
    if supporting < 2 or supporting_weight < 2.0:
        return "Weak evidence"
    _ = contradicting
    return "Agree"


def _band_weight(obj: dict[str, Any]) -> float:
    band = str(obj.get("confidence_band") or "").strip().lower()
    return _BAND_WEIGHT.get(band, 1.0)


def build_consensus_metrics(
    *,
    supporting: int,
    contradicting: int,
    neutral: int,
    supporting_weight: float,
    contradicting_weight: float,
) -> dict[str, Any]:
    """Additive metrics (A-403). Frozen count/label fields stay authoritative for UI."""
    polar = supporting + contradicting
    if polar == 0:
        support_ratio = None
        contested_ratio = None
        agreement_score = 0.0
    else:
        support_ratio = round(supporting / polar, 4)
        contested_ratio = round(contradicting / polar, 4)
        agreement_score = round((supporting - contradicting) / polar, 4)

    weight_total = supporting_weight + contradicting_weight
    if weight_total <= 0:
        weighted_support_ratio = None
    else:
        weighted_support_ratio = round(supporting_weight / weight_total, 4)

    return {
        "support_ratio": support_ratio,
        "contested_ratio": contested_ratio,
        "agreement_score": agreement_score,
        "weighted_supporting": round(supporting_weight, 4),
        "weighted_contradicting": round(contradicting_weight, 4),
        "weighted_support_ratio": weighted_support_ratio,
        "neutral": neutral,
        "polar_count": polar,
    }


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
    supporting_weight = 0.0
    contradicting_weight = 0.0

    for obj in objects:
        oid = int(obj.get("id") or 0)
        if not oid:
            continue
        stance = classify_stance(obj, binding_relation=binding_relations.get(oid))
        weight = _band_weight(obj)
        if stance == "supporting":
            supporting_ids.append(oid)
            supporting_weight += weight
        elif stance == "contradicting":
            contradicting_ids.append(oid)
            contradicting_weight += weight
        else:
            neutral_ids.append(oid)

    supporting = len(supporting_ids)
    contradicting = len(contradicting_ids)
    neutral = len(neutral_ids)
    label = consensus_label(
        supporting=supporting, contradicting=contradicting, neutral=neutral
    )
    metrics = build_consensus_metrics(
        supporting=supporting,
        contradicting=contradicting,
        neutral=neutral,
        supporting_weight=supporting_weight,
        contradicting_weight=contradicting_weight,
    )
    product = product_consensus_label(
        label=label,
        supporting=supporting,
        contradicting=contradicting,
        supporting_weight=supporting_weight,
    )

    return {
        "label": label,
        "product_label": product,
        "supporting": supporting,
        "contradicting": contradicting,
        "neutral": neutral,
        "supporting_ids": supporting_ids,
        "contradicting_ids": contradicting_ids,
        "neutral_ids": neutral_ids,
        # Additive (A-403 / RI-003)
        "metrics": metrics,
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
        "ranking_diagnostics": ranking_result.get("ranking_diagnostics"),
        "retrieval_version": ranking_result.get("retrieval_version"),
    }
