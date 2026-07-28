"""Unit tests for Evidence Retrieval helpers."""

from __future__ import annotations

from types import SimpleNamespace

from backend.evidence.retrieval import _match_score


def test_match_score_overlap():
    row = SimpleNamespace(claim="Drug X reduces HbA1c", quote="HbA1c decreased")
    assert _match_score(row, query_text="reduces HbA1c", selected_text="") > 0
    assert _match_score(row, query_text="unrelatedzzz", selected_text="") == 0


def test_match_score_empty_query():
    row = SimpleNamespace(claim="anything", quote="x")
    assert _match_score(row, query_text="", selected_text="") == 0.0
