"""Unit tests for scientific_structure extraction (Paper Analysis 2.1)."""

from backend.document_understanding.scientific_structure import extract_scientific_structure


def test_extracts_objectives_and_hypothesis_from_abstract_and_intro():
    payload = {
        "metadata": {
            "abstract": (
                "Background. Little is known about widget efficacy in adults. "
                "The aim of this study was to evaluate widget therapy in adults with fatigue."
            ),
            "title": "Widget Therapy Trial",
        },
        "structure": {
            "heading_order": ["1. Introduction", "2. Methods", "Results", "Discussion"],
            "raw_headings": {
                "1. Introduction": (
                    "Widgets are widely used. We hypothesize that widget therapy "
                    "improves fatigue scores versus placebo. Prior work is limited."
                ),
                "2. Methods": "A randomized controlled trial was conducted.",
                "Results": "Fatigue improved.",
                "Discussion": "Findings support the hypothesis under study.",
            },
            "section_types": {
                "1. Introduction": "introduction",
                "2. Methods": "methods",
                "Results": "results",
                "Discussion": "discussion",
            },
            "normalized_headings": {
                "introduction": "Widgets are widely used. We hypothesize that widget therapy "
                "improves fatigue scores versus placebo. Prior work is limited.",
                "methods": "A randomized controlled trial was conducted.",
            },
        },
    }

    out = extract_scientific_structure(payload)

    assert out["schema_version"] == "1.0.0"
    assert any(s["section_type"] == "methods" and s["present"] for s in out["section_skeleton"])
    assert out["objectives"], "expected at least one objective from abstract aim"
    assert "aim" in out["objectives"][0]["text"].lower() or "objective" in out["objectives"][0]["text"].lower()
    assert out["hypotheses"], "expected hypothesis from introduction"
    assert "hypothes" in out["hypotheses"][0]["text"].lower()
    assert out["problem_statement"] is None or "little is known" in (
        out["problem_statement"] or {}
    ).get("text", "").lower()


def test_dedicated_research_questions_heading():
    payload = {
        "metadata": {"abstract": ""},
        "structure": {
            "heading_order": ["Research Questions", "Methods"],
            "raw_headings": {
                "Research Questions": (
                    "RQ1: Does therapy A reduce pain versus usual care?\n"
                    "RQ2: Is adherence associated with outcome?"
                ),
                "Methods": "Survey design.",
            },
            "section_types": {
                "Research Questions": "other",
                "Methods": "methods",
            },
            "normalized_headings": {},
        },
    }

    out = extract_scientific_structure(payload)
    assert len(out["research_questions"]) >= 2
    assert out["research_questions"][0]["source"] == "heading"
    assert out["research_questions"][0]["confidence"] >= 0.85


def test_invent_nothing_on_empty_document():
    out = extract_scientific_structure({"metadata": {}, "structure": {}})
    assert out["objectives"] == []
    assert out["research_questions"] == []
    assert out["hypotheses"] == []
    assert out["problem_statement"] is None
    assert all(not s["present"] for s in out["section_skeleton"])


def test_serialize_document_attaches_scientific_structure():
    from datetime import datetime, timezone

    from backend.analysis_pipeline.models import AnalysisOptions
    from backend.analysis_pipeline.service import _serialize_document
    from backend.document_understanding.enums import SectionType
    from backend.document_understanding.models import (
        DocumentMetadata,
        DocumentQuality,
        DocumentStatistics,
        DocumentStructure,
        ProcessedDocument,
    )

    doc = ProcessedDocument(
        id="1",
        metadata=DocumentMetadata(
            title="T",
            abstract="The aim of this study was to compare A versus B in adults.",
        ),
        structure=DocumentStructure(
            heading_order=["Introduction", "Methods"],
            raw_headings={
                "Introduction": "Context for the reader.",
                "Methods": "RCT design.",
            },
            section_types={
                "Introduction": SectionType.INTRODUCTION,
                "Methods": SectionType.METHODS,
            },
            normalized_headings={
                SectionType.INTRODUCTION: "Context for the reader.",
                SectionType.METHODS: "RCT design.",
            },
        ),
        statistics=DocumentStatistics(),
        quality=DocumentQuality(),
        traceability={},
        full_text="x",
        schema_version="1",
        pipeline_version="1",
        processing_time_ms=1.0,
        created_at=datetime.now(timezone.utc),
    )
    payload = _serialize_document(doc, AnalysisOptions())
    assert isinstance(payload, dict)
    assert "scientific_structure" in payload
    assert payload["scientific_structure"]["objectives"]
    assert any(
        s["section_type"] == "methods" and s["present"]
        for s in payload["scientific_structure"]["section_skeleton"]
    )
