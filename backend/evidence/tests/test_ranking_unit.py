"""Unit tests for Evidence Ranking (Phase 2.3 Sprint 2)."""

from __future__ import annotations

import pytest

from backend.evidence.ranking import (
    apply_ranking_stage,
    default_v0_rank_key,
    rank_evidence_objects,
)


def _obj(**kwargs):
    base = {
        "id": 1,
        "status": "accepted",
        "confidence_band": "moderate",
        "study_quality": "",
        "study_type": "",
        "contradicts": [],
        "updated_at": None,
    }
    base.update(kwargs)
    return base


def test_default_v0_accepted_high_before_candidate():
    objects = [
        _obj(id=1, status="candidate", confidence_band="high", study_type="RCT", study_quality="High"),
        _obj(id=2, status="accepted", confidence_band="moderate", study_type="cohort", study_quality="Moderate"),
    ]
    ranked = rank_evidence_objects(objects, ranking_strategy="default_v0")
    assert [o["id"] for o in ranked] == [2, 1]


def test_default_v0_band_and_design_within_accepted():
    objects = [
        _obj(id=10, status="accepted", confidence_band="low", study_type="case report", study_quality="Low"),
        _obj(id=11, status="accepted", confidence_band="high", study_type="RCT", study_quality="High"),
        _obj(id=12, status="accepted", confidence_band="moderate", study_type="cohort", study_quality="Moderate"),
    ]
    ranked = rank_evidence_objects(objects, ranking_strategy="default_v0")
    assert [o["id"] for o in ranked] == [11, 12, 10]


def test_default_v0_contradiction_penalty():
    objects = [
        _obj(id=1, status="accepted", confidence_band="high", study_type="RCT", study_quality="High", contradicts=["other"]),
        _obj(id=2, status="accepted", confidence_band="high", study_type="RCT", study_quality="High", contradicts=[]),
    ]
    ranked = rank_evidence_objects(objects, ranking_strategy="default_v0")
    assert [o["id"] for o in ranked] == [2, 1]


def test_default_v0_recency_tiebreak():
    objects = [
        _obj(id=1, status="accepted", confidence_band="high", study_type="RCT", study_quality="High", updated_at="2024-01-01T00:00:00+00:00"),
        _obj(id=2, status="accepted", confidence_band="high", study_type="RCT", study_quality="High", updated_at="2025-06-01T00:00:00+00:00"),
    ]
    ranked = rank_evidence_objects(objects, ranking_strategy="default_v0")
    assert [o["id"] for o in ranked] == [2, 1]


def test_rank_does_not_mutate_or_invent():
    a = _obj(id=5, claim="same")
    b = _obj(id=6, claim="same")
    ranked = rank_evidence_objects([a, b], ranking_strategy="default_v0")
    assert {id(o) for o in ranked} == {id(a), id(b)}
    assert len(ranked) == 2
    assert {o["id"] for o in ranked} == {5, 6}


def test_unsupported_strategy_raises():
    with pytest.raises(ValueError, match="unsupported ranking_strategy"):
        rank_evidence_objects([_obj()], ranking_strategy="neural_v9")


def test_apply_ranking_stage_envelope():
    retrieval = {
        "query": {"ranking_strategy": "default_v0", "intent": "list_project"},
        "objects": [
            _obj(id=1, status="candidate", confidence_band="high"),
            _obj(id=2, status="accepted", confidence_band="low"),
        ],
        "total": 2,
        "truncated": False,
        "stage": "retrieval",
        "retrieval_version": "1.0.0",
    }
    out = apply_ranking_stage(retrieval)
    assert out["stage"] == "ranking"
    assert out["ranking_version"] == "1.0.0"
    assert out["ranking_strategy"] == "default_v0"
    assert out["objects"][0]["id"] == 2
    assert out["retrieval_version"] == "1.0.0"


def test_rank_key_ordering_tuple():
    weak = default_v0_rank_key(_obj(status="candidate", confidence_band="low"))
    strong = default_v0_rank_key(_obj(status="accepted", confidence_band="high", study_type="RCT", study_quality="High"))
    assert strong > weak
