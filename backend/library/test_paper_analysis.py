"""Tests for paper_analysis readiness helpers."""

from __future__ import annotations

from backend.library.paper_analysis import (
    batch_paper_analysis_status,
    cross_paper_research_ready,
    enrich_file_payload,
    normalize_analysis_status,
)


class _FakeCol:
    def __init__(self, name: str):
        self.name = name

    def in_(self, _ids):
        return self

    def __eq__(self, other):
        return (self, other)


class _FakePaperAnalysis:
    file_id = _FakeCol("file_id")
    status = _FakeCol("status")


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _stmt):
        return self

    def all(self):
        return self._rows


def test_normalize_analysis_status_defaults():
    assert normalize_analysis_status(None) == "pending"
    assert normalize_analysis_status("DONE") == "done"
    assert normalize_analysis_status("weird") == "pending"


def test_cross_paper_research_ready_only_done():
    assert cross_paper_research_ready("done") is True
    assert cross_paper_research_ready("pending") is False
    assert cross_paper_research_ready("running") is False


def test_batch_paper_analysis_status_fills_missing():
    db = _FakeDb([(1, "done"), (3, "running")])

    class _Stmt:
        def where(self, _cond):
            return db

    def select_fn(*_cols):
        return _Stmt()

    out = batch_paper_analysis_status(db, [1, 2, 3], _FakePaperAnalysis, select_fn)
    assert out[1] == "done"
    assert out[2] == "pending"
    assert out[3] == "running"


def test_enrich_file_payload():
    payload = enrich_file_payload({"id": 9}, "done")
    assert payload["paper_analysis_status"] == "done"
    assert payload["cross_paper_research_ready"] is True
