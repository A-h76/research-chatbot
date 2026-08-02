"""Unit tests for Evidence Consensus (Phase 2.3 Sprint 3)."""

from __future__ import annotations

from backend.evidence.consensus import (
    aggregate_consensus,
    apply_consensus_stage,
    classify_stance,
    consensus_label,
)


def _obj(oid: int, **kwargs):
    base = {
        "id": oid,
        "status": "accepted",
        "supports": [],
        "contradicts": [],
    }
    base.update(kwargs)
    return base


def test_classify_from_relation():
    assert classify_stance(_obj(1, relation="supports")) == "supporting"
    assert classify_stance(_obj(2, relation="contradicts")) == "contradicting"
    assert classify_stance(_obj(3, relation="related")) == "neutral"


def test_classify_from_arrays_and_binding_override():
    assert classify_stance(_obj(1, supports=["a"])) == "supporting"
    assert classify_stance(_obj(2, contradicts=["b"])) == "contradicting"
    assert classify_stance(_obj(3, supports=["a"], contradicts=["b", "c"])) == "contradicting"
    assert (
        classify_stance(_obj(4, contradicts=["x"]), binding_relation="supports") == "supporting"
    )


def test_classify_claim_bearing_without_supports_array():
    """Alpha path: accepted extract often has empty supports[] until KG edges exist."""
    assert (
        classify_stance(_obj(1, claim="Drug X reduces HbA1c", quote="…by 0.8%")) == "supporting"
    )
    assert classify_stance(_obj(2)) == "neutral"
    assert (
        classify_stance(_obj(3, claim="X", contradicts=["opposing finding"])) == "contradicting"
    )


def test_consensus_label_matrix():
    assert consensus_label(supporting=0, contradicting=0) == "none"
    assert consensus_label(supporting=0, contradicting=3) == "opposed"
    assert consensus_label(supporting=2, contradicting=2) == "contested"
    assert consensus_label(supporting=1, contradicting=2) == "contested"
    assert consensus_label(supporting=8, contradicting=2) == "strong"
    assert consensus_label(supporting=2, contradicting=0) == "strong"
    assert consensus_label(supporting=1, contradicting=0) == "moderate"
    assert consensus_label(supporting=3, contradicting=2) == "moderate"


def test_aggregate_counts_and_ids():
    objects = [
        _obj(1, relation="supports"),
        _obj(2, relation="supports"),
        _obj(3, relation="contradicts"),
        _obj(4, relation="related"),
        _obj(5, supports=["x"]),
    ]
    out = aggregate_consensus(objects)
    assert out["supporting"] == 3
    assert out["contradicting"] == 1
    assert out["neutral"] == 1
    assert out["label"] == "strong"
    assert out["supporting_ids"] == [1, 2, 5]
    assert set(out["contradicting_ids"]) == {3}
    assert set(out["neutral_ids"]) == {4}


def test_apply_consensus_stage_preserves_objects():
    ranked = {
        "query": {"intent": "answer_question"},
        "objects": [_obj(10, relation="supports"), _obj(11, relation="contradicts")],
        "total": 2,
        "truncated": False,
        "stage": "ranking",
        "ranking_version": "1.0.0",
        "ranking_strategy": "default_v0",
        "retrieval_version": "1.0.0",
    }
    out = apply_consensus_stage(ranked)
    assert out["stage"] == "consensus"
    assert out["consensus_version"] == "1.2.0"
    assert [o["id"] for o in out["objects"]] == [10, 11]
    assert out["consensus"]["label"] == "contested"
    assert out["consensus"]["product_label"] == "Mixed"
    assert out["ranking_strategy"] == "default_v0"
    m = out["consensus"]["metrics"]
    assert m["support_ratio"] == 0.5
    assert m["agreement_score"] == 0.0
    assert m["polar_count"] == 2


def test_product_label_agree_disagree_weak():
    from backend.evidence.consensus import product_consensus_label

    assert (
        product_consensus_label(label="strong", supporting=4, contradicting=1, supporting_weight=8.0)
        == "Agree"
    )
    assert (
        product_consensus_label(label="opposed", supporting=0, contradicting=3, supporting_weight=0.0)
        == "Disagree"
    )
    assert (
        product_consensus_label(label="moderate", supporting=1, contradicting=0, supporting_weight=1.0)
        == "Weak evidence"
    )
    assert (
        product_consensus_label(label="none", supporting=0, contradicting=0, supporting_weight=0.0)
        == "Weak evidence"
    )


def test_consensus_metrics_strong_support():
    objects = [
        _obj(1, relation="supports", confidence_band="high"),
        _obj(2, relation="supports", confidence_band="high"),
        _obj(3, relation="contradicts", confidence_band="low"),
    ]
    out = aggregate_consensus(objects)
    assert out["label"] == "strong"
    assert out["metrics"]["support_ratio"] == round(2 / 3, 4)
    assert out["metrics"]["weighted_supporting"] == 6.0
    assert out["metrics"]["weighted_contradicting"] == 1.0
    assert out["metrics"]["weighted_support_ratio"] == round(6 / 7, 4)
