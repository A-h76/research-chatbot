"""Unit tests for shared RI response envelope helpers."""

from __future__ import annotations

import pytest

from backend.evidence.envelope import collect_versions, stamp_ri_envelope


def test_collect_versions_from_scattered_fields():
    versions = collect_versions(
        {
            "retrieval_version": "1.0.0",
            "ranking_version": "1.0.0",
            "consensus_version": "",
            "conflict_version": None,
            "reasoning_version": "1.0.0",
        }
    )
    assert versions == {
        "retrieval": "1.0.0",
        "ranking": "1.0.0",
        "reasoning": "1.0.0",
    }


def test_stamp_ri_envelope_adds_timing_and_versions():
    out = stamp_ri_envelope(
        {
            "query": {"intent": "list_project"},
            "objects": [{"id": 1}],
            "total": 1,
            "truncated": False,
            "stage": "retrieval",
            "retrieval_version": "1.0.0",
        },
        timing_ms=12.6,
    )
    assert out["stage"] == "retrieval"
    assert out["timing_ms"] == 13
    assert out["versions"] == {"retrieval": "1.0.0"}
    assert out["retrieval_version"] == "1.0.0"  # legacy field preserved


def test_stamp_ri_envelope_defaults_missing_base_fields():
    out = stamp_ri_envelope({"stage": "ranking", "ranking_version": "1.0.0"}, timing_ms=0)
    assert out["query"] == {}
    assert out["objects"] == []
    assert out["total"] == 0
    assert out["truncated"] is False
    assert out["timing_ms"] == 0


def test_stamp_ri_envelope_requires_stage():
    with pytest.raises(ValueError, match="stage"):
        stamp_ri_envelope({"objects": []})
