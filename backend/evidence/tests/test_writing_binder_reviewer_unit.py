"""Unit tests for Citation Binder + Research Reviewer (Sprint B)."""

from __future__ import annotations

from backend.evidence.writing.citation_binder import (
    bind_citations_to_sections,
    flatten_bindings,
    parse_marker_ids,
)
from backend.evidence.writing.reviewer import review_grounded_draft


def test_parse_marker_ids_stable_unique_order():
    assert parse_marker_ids("A [#3] then [#1] and [#3] again [#2].") == [3, 1, 2]


def test_binder_resolves_markers_and_flags_orphans():
    sections = [
        {
            "id": "themes",
            "status": "ok",
            "paragraph": "Benefit shown [#1]. Unknown cite [#99]. Also [#2].",
            "citations": [
                {
                    "evidence_id": 2,
                    "claim": "B",
                    "quote": "qb",
                    "page": 3,
                    "file_id": 9,
                    "confidence_band": "high",
                }
            ],
            "evidence_ids": [2],
        }
    ]
    objects = [
        {"id": 1, "file_id": 9, "page": 1, "claim": "A", "quote": "qa", "confidence_band": "high"},
        {"id": 2, "file_id": 9, "page": 3, "claim": "B", "quote": "qb", "confidence_band": "high"},
    ]
    out = bind_citations_to_sections(sections=sections, objects=objects)
    assert out[0]["orphan_ids"] == [99]
    assert out[0]["marker_ids"] == [1, 99, 2]
    assert out[0]["evidence_ids"] == [1, 2]
    assert [b["evidence_id"] for b in out[0]["bindings"]] == [1, 2]
    assert flatten_bindings(out)[0]["evidence_id"] == 1


def test_reviewer_passes_bound_marked_sections():
    sections = [
        {
            "id": "themes",
            "title": "Themes",
            "status": "ok",
            "paragraph": "Drug X helps outcomes [#1].",
            "evidence_ids": [1],
            "bindings": [{"evidence_id": 1, "claim": "c", "confidence_band": "high"}],
            "orphan_ids": [],
        },
        {
            "id": "key_findings",
            "title": "Findings",
            "status": "ok",
            "paragraph": "Safety acceptable at 12 weeks [#2].",
            "evidence_ids": [2],
            "bindings": [{"evidence_id": 2, "claim": "d", "confidence_band": "moderate"}],
            "orphan_ids": [],
        },
    ]
    review = review_grounded_draft(
        sections=sections,
        consensus={"label": "strong"},
        conflict={},
        supporting_count=2,
    )
    assert review["status"] == "pass"
    assert review["name"] == "research_reviewer"
    assert review["pass_rate"] == 1.0
    assert review["metrics"]["unsupported_claims"] == 0
    assert review["metrics"]["grounding_pct"] == 1.0
    assert review["metrics"]["citation_coverage_pct"] == 1.0


def test_reviewer_fails_unbound_paragraph():
    sections = [
        {
            "id": "themes",
            "title": "Themes",
            "status": "ok",
            "paragraph": "ungrounded prose with no markers",
            "evidence_ids": [],
            "bindings": [],
            "orphan_ids": [],
        }
    ]
    review = review_grounded_draft(sections=sections)
    assert review["status"] == "fail"
    assert any(i["code"] == "unbound_paragraph" for i in review["issues"])


def test_reviewer_flags_unsupported_and_weak_evidence():
    sections = [
        {
            "id": "themes",
            "title": "Themes",
            "status": "ok",
            "paragraph": "This sentence has a cite [#1]. This sentence invents a fact.",
            "evidence_ids": [1],
            "bindings": [{"evidence_id": 1, "claim": "c", "confidence_band": "low"}],
            "orphan_ids": [],
        }
    ]
    review = review_grounded_draft(sections=sections, supporting_count=1)
    assert review["status"] == "fail"
    codes = {i["code"] for i in review["issues"]}
    assert "unsupported_claim" in codes
    assert "weak_evidence" in codes
    assert review["metrics"]["unsupported_claims"] >= 1


def test_reviewer_flags_orphan_citation():
    sections = [
        {
            "id": "themes",
            "title": "Themes",
            "status": "ok",
            "paragraph": "Claim with ghost cite [#1][#99].",
            "evidence_ids": [1],
            "bindings": [{"evidence_id": 1, "claim": "c", "confidence_band": "high"}],
            "orphan_ids": [99],
        }
    ]
    review = review_grounded_draft(sections=sections)
    assert review["status"] == "fail"
    assert any(i["code"] == "orphan_citation" for i in review["issues"])
