"""Unit tests for RI-006 Research Gap Engine."""

from __future__ import annotations

from backend.evidence.gaps import GAPS_VERSION, discover_gaps, gaps_to_markdown
from backend.evidence.matrix import build_evidence_matrix
from backend.evidence.themes import discover_themes


def _obj(oid, claim, *, file_id=1, **kw):
    base = {
        "id": oid,
        "file_id": file_id,
        "claim": claim,
        "quote": claim,
        "study_type": "",
        "supports": [],
        "contradicts": [],
        "limitations": [],
        "status": "accepted",
        "content_hash": f"h{oid}",
    }
    base.update(kw)
    return base


def test_discover_gaps_from_matrix_and_themes():
    objects = [
        _obj(1, "Alpha beta gamma finding one"),
        _obj(2, "Completely unrelated quantum optics", file_id=2),
    ]
    papers = [
        {"id": 1, "title": "Paper A"},
        {"id": 2, "title": "Paper B"},
    ]
    themes = discover_themes(objects, project_id=3, min_cluster_size=2)
    matrix = build_evidence_matrix(
        project_id=3,
        papers=papers,
        evidence_by_file={1: [objects[0]], 2: [objects[1]]},
        analysis_by_file={},
    )
    conflict = {
        "links": [{"a_id": 1, "b_id": 2, "unexplained": True, "mediators": []}],
    }
    out = discover_gaps(
        project_id=3,
        papers=papers,
        evidence_objects=objects,
        themes_payload=themes,
        matrix_payload=matrix,
        conflict_payload=conflict,
        consensus_payload={"product_label": "Weak evidence", "label": "none", "neutral_ids": [1, 2]},
    )
    assert out["stage"] == "gaps"
    assert out["gaps_version"] == GAPS_VERSION
    types = {g["type"] for g in out["gaps"]}
    assert "missing_matrix_cell" in types or "coverage" in types or "unexplained_conflict" in types
    assert "unexplained_conflict" in types
    assert "weak_consensus" in types
    for g in out["gaps"]:
        for eid in g["evidence_ids"]:
            assert eid in {1, 2}
        assert g["suggested_questions"]
    md = gaps_to_markdown(out)
    assert "Research Gaps" in md
