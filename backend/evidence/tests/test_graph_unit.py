"""Unit tests for RI-005 project graph."""

from __future__ import annotations

from backend.evidence.graph import GRAPH_VERSION, build_project_graph
from backend.evidence.themes import discover_themes


def _obj(oid, claim, *, file_id=1, **kw):
    base = {
        "id": oid,
        "file_id": file_id,
        "claim": claim,
        "quote": claim,
        "study_type": "RCT",
        "supports": ["x"],
        "contradicts": [],
        "status": "accepted",
        "content_hash": f"h{oid}",
    }
    base.update(kw)
    return base


def test_build_project_graph_nodes_and_edges():
    objects = [
        _obj(1, "Cognitive therapy reduces anxiety"),
        _obj(2, "Cognitive therapy for anxiety disorders", file_id=1),
        _obj(3, "Metformin glycemic control diabetes", file_id=2, supports=[], contradicts=["y"]),
    ]
    papers = [
        {"id": 1, "title": "Paper A", "year": "2020"},
        {"id": 2, "title": "Paper B", "year": "2021"},
    ]
    themes = discover_themes(objects, project_id=1, min_cluster_size=2)
    conflict_links = [{"a_id": 1, "b_id": 3, "mediators": ["method_differs"], "unexplained": False}]
    g = build_project_graph(
        project_id=1,
        papers=papers,
        evidence_objects=objects,
        themes_payload=themes,
        conflict_links=conflict_links,
    )
    assert g["stage"] == "graph"
    assert g["graph_version"] == GRAPH_VERSION
    types = {n["type"] for n in g["nodes"]}
    assert {"paper", "evidence", "theme"} <= types
    assert any(n["id"] == "paper:1" for n in g["nodes"])
    assert any(n["id"] == "evidence:1" for n in g["nodes"])
    edge_types = {e["type"] for e in g["edges"]}
    assert "from" in edge_types
    assert "in_theme" in edge_types or g["metrics"]["theme_count"] == 0
    assert "contradicts" in edge_types
    # No invented evidence ids
    ev_ids = {int(n["ref"]["evidence_id"]) for n in g["nodes"] if n["type"] == "evidence"}
    assert ev_ids == {1, 2, 3}
    g2 = build_project_graph(
        project_id=1,
        papers=papers,
        evidence_objects=objects,
        themes_payload=themes,
        conflict_links=conflict_links,
    )
    assert g["run"]["input_hash"] == g2["run"]["input_hash"]
