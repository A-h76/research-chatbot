"""Unit tests for Literature Review Markdown export (Sprint C)."""

from __future__ import annotations

from backend.evidence.writing.export_markdown import (
    build_literature_review_markdown,
    compute_export_traceability,
)


def test_export_contains_body_appendix_bibliography_metadata():
    writing = {
        "status": "ok",
        "mode": "grounded_v0",
        "section_type": "literature_review",
        "disclaimer": "Verify against sources.",
        "paragraph": "Benefit shown [#1].",
        "sections": [
            {
                "id": "themes",
                "status": "ok",
                "paragraph": "Benefit shown [#1].",
                "evidence_ids": [1],
                "bindings": [
                    {
                        "evidence_id": 1,
                        "page": 4,
                        "claim": "Drug X helps",
                        "quote": "significant reduction",
                        "confidence_band": "high",
                        "study_type": "RCT",
                    }
                ],
                "orphan_ids": [],
            }
        ],
        "bibliography": [
            {
                "evidence_id": 1,
                "page": 4,
                "claim": "Drug X helps",
                "quote": "significant reduction",
                "confidence_band": "high",
                "study_type": "RCT",
            }
        ],
        "citations": [],
        "metrics": {
            "grounding_pct": 1.0,
            "citation_coverage": 1.0,
            "unsupported_claims": 0,
            "unique_evidence_cited": 1,
        },
        "review": {
            "status": "pass",
            "pass_rate": 1.0,
            "metrics": {
                "grounding_pct": 1.0,
                "citation_coverage_pct": 1.0,
                "unsupported_claims": 0,
            },
        },
    }
    md = build_literature_review_markdown(
        title="HbA1c review",
        body="Benefit shown [#1].",
        writing=writing,
        writing_version="1.3.1",
        exported_at="2026-07-29T12:00:00+00:00",
    )
    assert md.startswith("# HbA1c review\n")
    assert "## Literature review" in md
    assert "Benefit shown [#1]." in md
    assert "## Evidence appendix" in md
    assert "### Evidence #1" in md
    assert "significant reduction" in md
    assert "## Bibliography" in md
    assert "1. [#1] Drug X helps, page 4" in md
    assert "## Generation metadata" in md
    assert "writing_version: 1.3.1" in md
    assert "evidence_traceability_100: yes" in md
    assert "research_reviewer: pass" in md


def test_traceability_fails_without_bindings():
    writing = {
        "sections": [
            {
                "id": "themes",
                "status": "ok",
                "paragraph": "ungrounded",
                "bindings": [],
                "evidence_ids": [],
            }
        ]
    }
    trace = compute_export_traceability(writing)
    assert trace["meets_100"] is False
    assert trace["traceability_pct"] == 0.0
