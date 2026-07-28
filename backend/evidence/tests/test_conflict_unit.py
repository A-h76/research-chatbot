"""Unit tests for Evidence Conflict (Phase 2.3 Sprint 4)."""

from __future__ import annotations

from backend.evidence.conflict import (
    analyze_conflicts,
    apply_conflict_stage,
    detect_mediators,
    extract_facets,
)


def _obj(oid: int, **kwargs):
    base = {
        "id": oid,
        "status": "accepted",
        "claim": "",
        "quote": "",
        "study_type": "",
        "supports": [],
        "contradicts": [],
        "limitations": [],
        "provenance": {},
    }
    base.update(kwargs)
    return base


def test_extract_facets_population_dosage_method_outcome():
    obj = _obj(
        1,
        claim="In adults, 10 mg once daily reduced HbA1c",
        study_type="RCT",
        supports=["HbA1c reduction"],
        provenance={"population": "adults"},
    )
    facets = extract_facets(obj)
    assert "adults" in facets["population"]
    assert any("10 mg" in d or "once daily" in d for d in facets["dosage"])
    assert "rct" in facets["method"]
    assert "hba1c reduction" in facets["outcome"]


def test_detect_mediators_method_and_population():
    a = _obj(
        1,
        relation="supports",
        study_type="RCT",
        claim="Drug X reduces HbA1c in adults",
        supports=["HbA1c reduction"],
    )
    b = _obj(
        2,
        relation="contradicts",
        study_type="cohort",
        claim="Drug X null on HbA1c in children",
        contradicts=["HbA1c reduction"],
    )
    mediators = detect_mediators(a, b)
    assert "method_differs" in mediators
    assert "population_differs" in mediators


def test_detect_dosage_and_outcome_differs():
    a = _obj(1, claim="High-dose 50 mg", supports=["weight loss"], study_type="RCT")
    b = _obj(2, claim="Low-dose 5 mg", supports=["blood pressure"], study_type="RCT")
    mediators = detect_mediators(a, b)
    assert "dosage_differs" in mediators
    assert "outcome_differs" in mediators


def test_analyze_conflicts_links_support_vs_contradict():
    objects = [
        _obj(1, relation="supports", study_type="RCT", claim="adults", supports=["A"]),
        _obj(2, relation="supports", study_type="RCT", claim="adults", supports=["A"]),
        _obj(3, relation="contradicts", study_type="cohort", claim="children", contradicts=["A"]),
        _obj(4, relation="related"),
    ]
    out = analyze_conflicts(objects)
    assert out["has_conflict"] is True
    assert out["supporting_ids"] == [1, 2]
    assert out["contradicting_ids"] == [3]
    assert out["pair_count"] == 2
    assert "method_differs" in out["mediators"]
    assert "population_differs" in out["mediators"]
    for link in out["links"]:
        assert link["a_stance"] == "supporting"
        assert link["b_stance"] == "contradicting"
        assert link["a_id"] in {1, 2}
        assert link["b_id"] == 3


def test_no_conflict_when_one_sided():
    objects = [
        _obj(1, relation="supports", supports=["A"]),
        _obj(2, relation="supports", supports=["A"]),
    ]
    out = analyze_conflicts(objects)
    assert out["has_conflict"] is False
    assert out["mediators"] == []
    assert out["links"] == []


def test_apply_conflict_stage_envelope():
    consensus = {
        "query": {"intent": "answer_question"},
        "objects": [
            _obj(10, relation="supports", study_type="RCT", supports=["x"]),
            _obj(11, relation="contradicts", study_type="case report", contradicts=["x"]),
        ],
        "total": 2,
        "truncated": False,
        "stage": "consensus",
        "consensus_version": "1.0.0",
        "consensus": {
            "label": "contested",
            "supporting": 1,
            "contradicting": 1,
            "neutral": 0,
            "supporting_ids": [10],
            "contradicting_ids": [11],
            "neutral_ids": [],
        },
        "ranking_version": "1.0.0",
        "ranking_strategy": "default_v0",
        "retrieval_version": "1.0.0",
    }
    out = apply_conflict_stage(consensus)
    assert out["stage"] == "conflict"
    assert out["conflict_version"] == "1.0.0"
    assert out["conflict"]["has_conflict"] is True
    assert "method_differs" in out["conflict"]["mediators"]
    assert out["consensus"]["label"] == "contested"
    assert [o["id"] for o in out["objects"]] == [10, 11]
