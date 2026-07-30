"""Unit tests for durable Reviewer run persistence (A-401 / A-503)."""

from __future__ import annotations

from backend.evidence.writing.reviewer_persistence import (
    build_input_snapshot,
    enrich_issues_with_evidence_ids,
    persist_reviewer_run,
    serialize_run,
)


class _FakeDB:
    def __init__(self):
        self.added = []
        self._next_id = 1

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None and obj.__class__.__name__ == "ReviewerRun":
            obj.id = self._next_id
            self._next_id += 1

    def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1


class ReviewerRun:
    def __init__(self, **kwargs):
        self.id = None
        for k, v in kwargs.items():
            setattr(self, k, v)


class ReviewerFinding:
    def __init__(self, **kwargs):
        self.id = None
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_enrich_issues_pulls_section_evidence_ids():
    issues = [{"code": "ungrounded", "severity": "error", "section_id": "s1", "message": "x"}]
    sections = [
        {
            "id": "s1",
            "bindings": [{"evidence_id": 10}, {"evidence_id": 11}],
            "evidence_ids": [11, 12],
        }
    ]
    out = enrich_issues_with_evidence_ids(issues, sections)
    assert out[0]["evidence_ids"] == [10, 11, 12]


def test_build_input_snapshot_is_stable():
    snap = build_input_snapshot(
        sections=[
            {
                "id": "intro",
                "title": "Intro",
                "status": "ok",
                "paragraph": "Claim text [#1].",
                "bindings": [{"evidence_id": 1}],
            }
        ],
        consensus={"label": "aligned"},
        conflict={"has_conflict": False, "mediators": []},
        supporting_count=1,
    )
    assert snap["evidence_ids"] == [1]
    assert snap["sections"][0]["paragraph_hash"]
    assert "Claim text" in snap["sections"][0]["paragraph_preview"]


def test_persist_and_serialize_reconstructs_review():
    db = _FakeDB()
    review = {
        "reviewer_version": "1.1.0",
        "status": "fail",
        "pass_rate": 0.5,
        "sections_checked": 2,
        "sections_passed": 1,
        "issue_count": 1,
        "issues": [
            {
                "code": "empty_section",
                "severity": "error",
                "section_id": "s2",
                "message": "empty",
            }
        ],
        "metrics": {"grounding_pct": 50.0},
    }
    run = persist_reviewer_run(
        db,
        ReviewerRun=ReviewerRun,
        ReviewerFinding=ReviewerFinding,
        user_id=1,
        project_id=2,
        document_id=3,
        document_version_no=4,
        writing_version="1.3.1",
        review=review,
        sections=[{"id": "s2", "bindings": [{"evidence_id": 99}], "paragraph": ""}],
        consensus={"label": "aligned"},
        conflict={"has_conflict": False},
        supporting_count=0,
        prompt_meta={"reviewer_kind": "rule_based"},
    )
    findings = [o for o in db.added if isinstance(o, ReviewerFinding)]
    assert run.id == 1
    assert run.reviewer_version == "1.1.0"
    assert run.model_version_id is None
    assert findings and findings[0].evidence_ids_json == "[99]"

    payload = serialize_run(run, findings=findings)
    assert payload["review"]["reviewer_version"] == "1.1.0"
    assert payload["review"]["issues"][0]["code"] == "empty_section"
    assert payload["review"]["issues"][0]["evidence_ids"] == [99]
    assert payload["input_snapshot"]["evidence_ids"] == [99]
    assert payload["prompt_meta"]["reviewer_kind"] == "rule_based"
    assert "confidence" in payload["metrics"]
