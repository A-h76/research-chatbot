"""Unit tests for RI-007 Research Timeline."""

from __future__ import annotations

from backend.evidence.timeline import TIMELINE_VERSION, build_timeline, timeline_to_markdown
from backend.evidence.themes import discover_themes


def _obj(oid, claim, *, file_id=1, year=None, **kw):
    base = {
        "id": oid,
        "file_id": file_id,
        "claim": claim,
        "quote": claim,
        "study_type": "RCT",
        "supports": [],
        "status": "accepted",
        "content_hash": f"h{oid}",
        "provenance": {"year": year} if year else {},
    }
    base.update(kw)
    return base


def test_timeline_buckets_and_evolution():
    papers = [
        {"id": 1, "title": "A", "year": "2018"},
        {"id": 2, "title": "B", "year": "2021"},
        {"id": 3, "title": "C", "year": ""},
    ]
    objects = [
        _obj(1, "Cognitive therapy anxiety 2018 cohort", file_id=1),
        _obj(2, "Cognitive therapy anxiety follow-up", file_id=1),
        _obj(3, "Metformin diabetes control", file_id=2),
        _obj(4, "Undated claim without year", file_id=3),
    ]
    themes = discover_themes(objects, project_id=1, min_cluster_size=2)
    out = build_timeline(
        project_id=1, papers=papers, evidence_objects=objects, themes_payload=themes
    )
    assert out["stage"] == "timeline"
    assert out["timeline_version"] == TIMELINE_VERSION
    years = [e["year"] for e in out["entries"]]
    assert 2018 in years and 2021 in years
    for e in out["entries"]:
        assert e["evidence_ids"] or e["file_ids"]
    assert out["span"]["start_year"] == 2018
    assert out["metrics"]["paper_count"] == 3
    md = timeline_to_markdown(out)
    assert "Research Timeline" in md
    out2 = build_timeline(
        project_id=1, papers=papers, evidence_objects=objects, themes_payload=themes
    )
    assert out["run"]["input_hash"] == out2["run"]["input_hash"]
