"""Evidence Query v0 contract tests (Phase 2.3 Sprint 0)."""

from __future__ import annotations

import json
from pathlib import Path

from backend.evidence.query import FORBIDDEN_KEYS, normalize_evidence_query

FIXTURE = Path("tests/fixtures/evidence/evidence_query_v0.json")


def test_fixture_normalizes():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    q = normalize_evidence_query(raw, user_id=42)
    assert q["intent"] == "support_sentence"
    assert q["scope"]["user_id"] == 42
    assert q["scope"]["project_id"] == 2
    assert q["ranking_strategy"] == "default_v0"
    assert q["result_limit"] == 20
    assert "accepted" in q["filters"]["status"]


def test_rejects_model_knobs():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for key in sorted(FORBIDDEN_KEYS):
        bad = dict(raw)
        bad[key] = "nope"
        try:
            normalize_evidence_query(bad, user_id=1)
            assert False, f"expected reject for {key}"
        except ValueError as exc:
            assert key in str(exc) or "must not include" in str(exc)


def test_requires_project_and_valid_intent():
    try:
        normalize_evidence_query({"intent": "support_sentence", "scope": {}}, user_id=1)
        assert False
    except ValueError:
        pass
    try:
        normalize_evidence_query(
            {"intent": " invent", "scope": {"project_id": 1}},
            user_id=1,
        )
        assert False
    except ValueError:
        pass


def test_clamps_result_limit():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["result_limit"] = 999
    assert normalize_evidence_query(raw, user_id=1)["result_limit"] == 100


def test_default_and_valid_section_type():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    q = normalize_evidence_query(raw, user_id=1)
    assert q["section_type"] == "support_sentence"
    raw["section_type"] = "literature_review"
    assert normalize_evidence_query(raw, user_id=1)["section_type"] == "literature_review"
    try:
        normalize_evidence_query({**raw, "section_type": "blog_post"}, user_id=1)
        assert False
    except ValueError as exc:
        assert "section_type" in str(exc)
