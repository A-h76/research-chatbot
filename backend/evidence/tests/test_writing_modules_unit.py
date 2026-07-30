"""Unit tests for Writing Intelligence Planner / Context / Section (Milestone 1)."""

from __future__ import annotations

from backend.evidence.writing.context_builder import build_section_contexts
from backend.evidence.writing.metrics import compute_writing_metrics
from backend.evidence.writing.planner import plan_sections
from backend.evidence.writing.section_generator import generate_sections
from backend.evidence.writing_intelligence import (
    apply_writing_intelligence_stage,
    build_writing_intelligence,
    compose_grounded_paragraph,
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


def test_plan_introduction_has_three_slots():
    plan = plan_sections(section_type="introduction", topic="Drug X")
    assert plan["section_type"] == "introduction"
    assert plan["slot_count"] == 3
    assert [s["id"] for s in plan["slots"]] == ["problem", "significance", "overview"]


def test_context_builder_allocates_supporting_ids():
    plan = plan_sections(section_type="literature_review", topic="HbA1c")
    supporting = [
        _obj(1, claim="Drug X lowers HbA1c in adults"),
        _obj(2, claim="Drug X improves glycemic control"),
        _obj(3, claim="Safety profile acceptable at 12 weeks", confidence_band="low"),
        _obj(4, claim="Meta-analysis supports HbA1c reduction", study_type="meta-analysis"),
        _obj(5, claim="Population differences unexplained", confidence_band="low"),
        _obj(6, claim="Drug X reduces HbA1c versus placebo"),
    ]
    contexts = build_section_contexts(
        plan=plan,
        supporting=supporting,
        consensus={"label": "strong", "supporting_ids": [1, 2, 3, 4, 5, 6]},
        conflict={"has_conflict": True, "mediators": ["population_differs"]},
    )
    assert len(contexts) == 3
    assert [c["facet"] for c in contexts] == ["themes", "consensus", "conflict"]
    allocated = {eid for c in contexts for eid in c["evidence_ids"]}
    assert allocated == {1, 2, 3, 4, 5, 6}
    assert all(c["evidence_ids"] for c in contexts)
    assert all("structured_argument" in c for c in contexts)
    arg = contexts[0]["structured_argument"]
    assert arg["theme_clusters"]
    assert arg["consensus"]["label"] == "strong"
    assert arg["conflict"]["has_conflict"] is True
    assert arg["methodology"]
    assert arg["chronology"]


def test_section_generator_emits_headed_paragraphs():
    plan = plan_sections(section_type="discussion", topic="Drug X")
    supporting = [_obj(1, claim="Drug X helps"), _obj(2, claim="Safe at 12w"), _obj(3)]
    contexts = build_section_contexts(
        plan=plan,
        supporting=supporting,
        consensus={"label": "moderate"},
        conflict={"has_conflict": False},
    )
    sections = generate_sections(
        contexts=contexts, conflict={"has_conflict": False}, composer=compose_grounded_paragraph
    )
    assert len(sections) == 3
    assert sections[0]["status"] == "ok"
    assert sections[0]["paragraph"].startswith("**")
    assert sections[0]["evidence_ids"]


def test_build_writing_section_type_literature_review():
    objects = [_obj(i) for i in range(1, 7)]
    out = build_writing_intelligence(
        query={
            "query_text": "Drug X HbA1c",
            "section_type": "literature_review",
            "anchors": {"selected_text": "Drug X reduces HbA1c"},
        },
        objects=objects,
        reasoning={"sufficiency": "sufficient", "summary_code": "strong"},
        consensus={
            "label": "strong",
            "supporting_ids": [1, 2, 3, 4, 5, 6],
            "contradicting_ids": [],
        },
        conflict={"has_conflict": False, "mediators": []},
    )
    assert out["status"] == "ok"
    assert out["section_type"] == "literature_review"
    assert out["plan"]["slot_count"] == 3
    assert len(out["sections"]) == 3
    assert out["paragraph"] and "\n\n" in out["paragraph"]
    assert "[#" in out["paragraph"]
    assert out["metrics"]["grounding_pct"] >= 0.3
    assert out["metrics"]["unique_evidence_cited"] >= 1
    assert out["ri_context"] is not None


def test_apply_writing_version_bump():
    reasoned = {
        "query": {
            "intent": "support_sentence",
            "section_type": "support_sentence",
            "query_text": "HbA1c",
            "anchors": {},
        },
        "objects": [_obj(10)],
        "total": 1,
        "truncated": False,
        "stage": "reasoning",
        "reasoning_version": "1.0.0",
        "reasoning": {
            "sufficiency": "sufficient",
            "summary_code": "strong",
            "steps": [],
            "evidence_ids": [10],
        },
        "consensus": {
            "label": "strong",
            "supporting_ids": [10],
            "contradicting_ids": [],
            "neutral_ids": [],
        },
        "conflict": {"has_conflict": False, "mediators": []},
        "ranking_strategy": "default_v0",
        "retrieval_version": "1.0.0",
    }
    out = apply_writing_intelligence_stage(reasoned)
    assert out["writing_version"] == "2.0.0"
    assert out["writing"]["mode"] == "grounded_v1"
    assert out["writing"]["sections"]
    assert out["writing"]["metrics"] is not None
    assert out["writing"]["review"] is not None
    assert out["writing"]["bibliography"] is not None
    assert out["writing"]["ri_context"] is not None


def test_metrics_unsupported_when_empty_slots():
    metrics = compute_writing_metrics(
        sections=[{"status": "empty"}, {"status": "ok", "evidence_ids": [1]}],
        supporting_count=2,
        citations=[{"evidence_id": 1}],
    )
    assert metrics["unsupported_sentence_rate"] == 0.5
    assert metrics["grounding_pct"] == 0.5
    assert metrics["citation_coverage"] == 0.5
