"""Unit tests for Evidence Reasoning (Phase 2.3 Sprint 5)."""

from __future__ import annotations

from backend.evidence.reasoning import (
    apply_reasoning_stage,
    build_reasoning,
    sufficiency_from_summary,
    summary_code_from_stages,
)


def test_summary_code_matrix():
    assert summary_code_from_stages(consensus=None, conflict=None, object_count=0) == "insufficient"
    assert (
        summary_code_from_stages(
            consensus={"label": "strong"}, conflict={"has_conflict": False}, object_count=3
        )
        == "strong"
    )
    assert (
        summary_code_from_stages(
            consensus={"label": "contested"},
            conflict={"has_conflict": True, "mediators": ["method_differs"]},
            object_count=2,
        )
        == "contested_with_mediators"
    )
    assert (
        summary_code_from_stages(
            consensus={"label": "contested"},
            conflict={"has_conflict": True, "mediators": []},
            object_count=2,
        )
        == "contested"
    )


def test_sufficiency_mapping():
    assert sufficiency_from_summary("strong") == "sufficient"
    assert sufficiency_from_summary("contested_with_mediators") == "weak"
    assert sufficiency_from_summary("insufficient") == "insufficient"


def test_build_reasoning_steps_are_templated():
    objects = [
        {"id": 1, "status": "accepted"},
        {"id": 2, "status": "accepted"},
    ]
    reasoning = build_reasoning(
        query={"intent": "answer_question", "ranking_strategy": "default_v0"},
        objects=objects,
        consensus={
            "label": "contested",
            "supporting": 1,
            "contradicting": 1,
            "neutral": 0,
        },
        conflict={
            "has_conflict": True,
            "mediators": ["method_differs", "population_differs"],
            "pair_count": 1,
        },
        total=2,
    )
    assert reasoning["summary_code"] == "contested_with_mediators"
    assert reasoning["evidence_ids"] == [1, 2]
    assert "Method differs" in reasoning["mediator_labels"]
    steps = {s["step"]: s for s in reasoning["steps"]}
    assert "retrieval" in steps and "ranking" in steps
    assert "consensus" in steps and "conflict" in steps
    assert steps["conclusion"]["code"] == "contested_with_mediators"
    assert "Method differs" in steps["conclusion"]["detail"]
    # No invented ids
    assert set(reasoning["evidence_ids"]).issubset({1, 2})


def test_apply_reasoning_stage_envelope():
    conflicted = {
        "query": {"intent": "list_project", "ranking_strategy": "default_v0"},
        "objects": [{"id": 10}, {"id": 11}],
        "total": 2,
        "truncated": False,
        "stage": "conflict",
        "conflict_version": "1.0.0",
        "conflict": {
            "has_conflict": False,
            "mediators": [],
            "pair_count": 0,
            "supporting_ids": [10, 11],
            "contradicting_ids": [],
        },
        "consensus": {
            "label": "strong",
            "supporting": 2,
            "contradicting": 0,
            "neutral": 0,
            "supporting_ids": [10, 11],
            "contradicting_ids": [],
            "neutral_ids": [],
        },
        "consensus_version": "1.0.0",
        "ranking_version": "1.0.0",
        "ranking_strategy": "default_v0",
        "retrieval_version": "1.0.0",
    }
    out = apply_reasoning_stage(conflicted)
    assert out["stage"] == "reasoning"
    assert out["reasoning_version"] == "1.0.0"
    assert out["reasoning"]["summary_code"] == "strong"
    assert out["reasoning"]["sufficiency"] == "sufficient"
    assert out["consensus"]["label"] == "strong"
    assert [o["id"] for o in out["objects"]] == [10, 11]
