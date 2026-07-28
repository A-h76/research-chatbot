"""Unit tests for Writing Intelligence (Phase 2.3 Sprint 6)."""

from __future__ import annotations

from backend.evidence.writing_intelligence import (
    apply_writing_intelligence_stage,
    build_writing_intelligence,
    compose_grounded_paragraph,
    decide_generation_gate,
)


def _obj(oid: int, **kwargs):
    base = {
        "id": oid,
        "file_id": 9,
        "page": 1,
        "claim": f"Claim {oid}",
        "quote": f"Quote {oid}",
        "supports": ["x"],
        "contradicts": [],
        "relation": "supports",
        "confidence_band": "high",
        "study_type": "RCT",
    }
    base.update(kwargs)
    return base


def test_gate_blocks_insufficient_and_opposed():
    status, reason = decide_generation_gate(
        reasoning={"sufficiency": "insufficient", "summary_code": "insufficient"},
        consensus={"label": "none"},
        supporting=[],
    )
    assert status == "blocked"
    assert reason in {"insufficient_evidence", "no_supporting_evidence"}

    status, reason = decide_generation_gate(
        reasoning={"sufficiency": "weak", "summary_code": "opposed"},
        consensus={"label": "opposed"},
        supporting=[],
    )
    assert status == "blocked"
    assert reason == "opposed_evidence"


def test_compose_uses_only_supporting_claims():
    supporting = [
        _obj(1, claim="Drug X reduces HbA1c", page=2),
        _obj(2, claim="Effect persists at 12 weeks", page=4),
    ]
    paragraph, citations, warnings = compose_grounded_paragraph(
        query={"query_text": "Drug X reduces HbA1c", "anchors": {"selected_text": ""}},
        supporting=supporting,
        conflict={"has_conflict": True, "mediators": ["method_differs"]},
    )
    assert "Drug X reduces HbA1c" in paragraph
    assert "Effect persists at 12 weeks" in paragraph
    assert "method" in paragraph
    assert [c["evidence_id"] for c in citations] == [1, 2]
    assert warnings


def test_build_writing_ok_and_blocked():
    objects = [_obj(1), _obj(2, relation="contradicts", supports=[], contradicts=["x"])]
    ok = build_writing_intelligence(
        query={"query_text": "topic", "anchors": {}},
        objects=objects,
        reasoning={"sufficiency": "sufficient", "summary_code": "strong"},
        consensus={"label": "strong", "supporting_ids": [1], "contradicting_ids": []},
        conflict={"has_conflict": False, "mediators": []},
    )
    assert ok["status"] == "ok"
    assert ok["paragraph"]
    assert ok["citations"][0]["evidence_id"] == 1
    assert "Evidence Layer" in ok["disclaimer"]

    blocked = build_writing_intelligence(
        query={},
        objects=[],
        reasoning={"sufficiency": "insufficient", "summary_code": "insufficient"},
        consensus={"label": "none", "supporting_ids": []},
        conflict={"has_conflict": False},
    )
    assert blocked["status"] == "blocked"
    assert blocked["paragraph"] is None


def test_apply_writing_stage_envelope():
    reasoned = {
        "query": {"intent": "support_sentence", "query_text": "HbA1c", "anchors": {}},
        "objects": [_obj(10)],
        "total": 1,
        "truncated": False,
        "stage": "reasoning",
        "reasoning_version": "1.0.0",
        "reasoning": {"sufficiency": "sufficient", "summary_code": "strong", "steps": [], "evidence_ids": [10]},
        "consensus": {"label": "strong", "supporting_ids": [10], "contradicting_ids": [], "neutral_ids": []},
        "conflict": {"has_conflict": False, "mediators": []},
        "ranking_strategy": "default_v0",
        "retrieval_version": "1.0.0",
    }
    out = apply_writing_intelligence_stage(reasoned)
    assert out["stage"] == "writing"
    assert out["writing_version"] == "1.0.0"
    assert out["writing"]["status"] == "ok"
    assert out["writing"]["mode"] == "grounded_v0"
    assert out["objects"][0]["id"] == 10
