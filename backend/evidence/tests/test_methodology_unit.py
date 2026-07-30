"""Unit tests for RI-008 Methodology Intelligence."""

from __future__ import annotations

from backend.evidence.methodology import (
    METHODOLOGY_VERSION,
    build_methodology_advice,
    methodology_to_markdown,
)
from backend.evidence.matrix import build_evidence_matrix
from backend.evidence.themes import discover_themes


def _obj(oid, claim, *, file_id=1, study_type="RCT", **kw):
    base = {
        "id": oid,
        "file_id": file_id,
        "claim": claim,
        "quote": claim,
        "study_type": study_type,
        "supports": ["anxiety"],
        "limitations": ["Small sample"],
        "status": "accepted",
        "content_hash": f"h{oid}",
        "provenance": {"statistics": "ANOVA"},
    }
    base.update(kw)
    return base


def test_methodology_advisory_cards():
    objects = [
        _obj(1, "Cognitive therapy anxiety"),
        _obj(2, "Cognitive therapy anxiety trial", study_type="RCT"),
        _obj(3, "Cohort anxiety outcomes", file_id=2, study_type="cohort"),
    ]
    papers = [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]
    themes = discover_themes(objects, project_id=2, min_cluster_size=2)
    matrix = build_evidence_matrix(
        project_id=2,
        papers=papers,
        evidence_by_file={1: objects[:2], 2: [objects[2]]},
        analysis_by_file={},
    )
    out = build_methodology_advice(
        project_id=2,
        papers=papers,
        evidence_objects=objects,
        themes_payload=themes,
        matrix_payload=matrix,
        consensus_payload={"product_label": "Mixed", "supporting_ids": [1], "contradicting_ids": [3]},
    )
    assert out["stage"] == "methodology"
    assert out["methodology_version"] == METHODOLOGY_VERSION
    assert out["disclaimer"]
    kinds = {c["kind"] for c in out["cards"]}
    assert "study_design" in kinds
    assert "threats_to_validity" in kinds or "statistics" in kinds
    for c in out["cards"]:
        assert c["tone"] == "advisory"
        # No imperative "must" / "you should run" style in advice (soft check)
        assert "must run" not in (c["advice"] or "").lower()
    md = methodology_to_markdown(out)
    assert "Methodology Intelligence" in md
