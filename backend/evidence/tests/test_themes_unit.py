"""Unit tests for RI-001 Theme Discovery."""

from __future__ import annotations

from backend.evidence.themes import (
    THEMES_VERSION,
    discover_themes,
    jaccard,
    object_tokens,
    reconstruct_fingerprint,
    themes_to_markdown,
)


def _obj(oid: int, claim: str, *, file_id: int = 1, study_type: str = "RCT", **kw):
    base = {
        "id": oid,
        "file_id": file_id,
        "claim": claim,
        "quote": claim,
        "study_type": study_type,
        "supports": [],
        "content_hash": f"h{oid}",
        "status": "accepted",
    }
    base.update(kw)
    return base


def test_jaccard_and_tokens():
    a = object_tokens(_obj(1, "Cognitive behavioral therapy reduces anxiety symptoms"))
    b = object_tokens(_obj(2, "Cognitive behavioral therapy for anxiety disorders"))
    c = object_tokens(_obj(3, "Metformin improves glycemic control in diabetes"))
    assert jaccard(a, b) > jaccard(a, c)
    assert "cognitive" in a or "behavioral" in a


def test_discover_themes_groups_related_and_is_deterministic():
    objects = [
        _obj(1, "Cognitive behavioral therapy reduces anxiety"),
        _obj(2, "Cognitive behavioral therapy for anxiety disorders", file_id=2),
        _obj(3, "CBT anxiety treatment outcomes"),
        _obj(4, "Metformin improves glycemic control diabetes"),
        _obj(5, "Metformin glycemic outcomes in type 2 diabetes", file_id=3),
        _obj(6, "Unrelated quantum optics interferometry", file_id=4),
    ]
    a = discover_themes(objects, project_id=7, min_cluster_size=2)
    b = discover_themes(objects, project_id=7, min_cluster_size=2)
    assert a["stage"] == "themes"
    assert a["themes_version"] == THEMES_VERSION
    assert a["run"]["input_hash"] == b["run"]["input_hash"]
    assert reconstruct_fingerprint(a) == reconstruct_fingerprint(b)
    assert a["metrics"]["theme_count"] >= 2
    labels = [t["label"] for t in a["themes"]]
    assert any(t.startswith("Theme A") for t in labels)
    # Every evidence id appears once across themes + unassigned
    seen = set()
    for t in a["themes"]:
        for eid in t["evidence_ids"]:
            assert eid not in seen
            seen.add(eid)
        assert t["sample_claims"]
        assert t["file_ids"]
    for eid in a["unassigned"]["evidence_ids"]:
        assert eid not in seen
        seen.add(eid)
    assert seen == {1, 2, 3, 4, 5, 6}

    md = themes_to_markdown(a)
    assert "# Theme Discovery" in md
    assert "Theme A" in md


def test_no_invented_ids():
    objects = [_obj(10, "Alpha beta gamma"), _obj(11, "Alpha beta delta")]
    out = discover_themes(objects, min_cluster_size=2)
    for t in out["themes"]:
        for eid in t["evidence_ids"]:
            assert eid in {10, 11}
