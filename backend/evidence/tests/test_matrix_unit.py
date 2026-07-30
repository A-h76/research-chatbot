"""Unit tests for RI-002 Evidence Matrix."""

from __future__ import annotations

from backend.evidence.matrix import (
    MATRIX_VERSION,
    build_evidence_matrix,
    build_row_for_paper,
    make_cell,
    matrix_to_csv,
    matrix_to_markdown,
)


def test_make_cell_unknown():
    cell = make_cell(value=None)
    assert cell["status"] == "unknown"
    assert cell["value"] is None
    assert cell["evidence_ids"] == []


def test_row_prefers_evidence_then_analysis_fallback():
    objs = [
        {
            "id": 11,
            "claim": "CBT reduces symptoms",
            "study_type": "RCT",
            "supports": [],
            "limitations": ["Small n"],
            "provenance": {"dataset": "NHANES"},
        }
    ]
    row = build_row_for_paper(
        file_id=1,
        paper_title="Demo Paper",
        paper_year="2020",
        evidence_objects=objs,
        analysis_data={
            "methodology": "survey",
            "dataset": "other",
            "results": "ignored when evidence present",
            "limitations": ["analysis lim"],
        },
    )
    assert row["method"]["value"] == "RCT"
    assert row["method"]["evidence_ids"] == [11]
    assert row["method"]["sources"] == ["evidence_object"]
    assert row["dataset"]["value"] == "NHANES"
    assert "CBT" in row["findings"]["value"]
    assert row["limitations"]["value"] == "Small n"
    assert row["evidence_count"] == 1


def test_row_marks_unknown_and_uses_analysis_when_no_evidence():
    row = build_row_for_paper(
        file_id=2,
        paper_title="Sparse",
        evidence_objects=[],
        analysis_data={
            "methodology": "meta-analysis",
            "dataset": "PubMed corpus",
            "results": "Effect size positive",
            "limitations": ["Publication bias"],
        },
    )
    assert row["method"]["value"] == "meta-analysis"
    assert row["method"]["sources"] == ["paper_analysis"]
    assert row["method"]["evidence_ids"] == []
    assert row["dataset"]["status"] == "known"
    assert row["findings"]["status"] == "known"
    assert row["limitations"]["status"] == "known"

    empty = build_row_for_paper(
        file_id=3, paper_title="Empty", evidence_objects=[], analysis_data={}
    )
    assert empty["method"]["status"] == "unknown"
    assert empty["dataset"]["status"] == "unknown"
    assert empty["findings"]["status"] == "unknown"
    assert empty["limitations"]["status"] == "unknown"


def test_build_matrix_metrics_and_exports():
    matrix = build_evidence_matrix(
        project_id=9,
        papers=[{"id": 1, "title": "A", "year": "2019"}, {"id": 2, "title": "B"}],
        evidence_by_file={
            1: [{"id": 5, "claim": "X works", "study_type": "cohort", "limitations": []}],
            2: [],
        },
        analysis_by_file={2: {"dataset": "MIMIC"}},
    )
    assert matrix["stage"] == "matrix"
    assert matrix["matrix_version"] == MATRIX_VERSION
    assert matrix["columns"] == ["paper", "method", "dataset", "findings", "limitations"]
    assert len(matrix["rows"]) == 2
    assert matrix["metrics"]["paper_count"] == 2
    assert matrix["metrics"]["papers_with_evidence"] == 1
    assert matrix["metrics"]["cell_known"] >= 3
    assert matrix["metrics"]["coverage"] is not None

    md = matrix_to_markdown(matrix)
    assert "| Paper | Method | Dataset | Findings | Limitations |" in md
    assert "_unknown_" in md or "MIMIC" in md
    assert "e:5" in md

    csv_text = matrix_to_csv(matrix)
    assert "file_id,paper_title" in csv_text
    assert "cohort" in csv_text
    assert "unknown" in csv_text
