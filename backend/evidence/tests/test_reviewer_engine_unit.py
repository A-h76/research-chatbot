"""Bite 4 — ACR-wrapped deterministic reviewer + ledger."""

from __future__ import annotations

from backend.ai.ai_ledger import clear_ledger_for_tests, recent_executions
from backend.evidence.writing.reviewer_engine import execute_reviewer


def _ok_section(paragraph: str, eid: int = 1):
    return {
        "id": "s1",
        "title": "Findings",
        "status": "ok",
        "paragraph": paragraph,
        "bindings": [
            {
                "evidence_id": eid,
                "confidence_band": "high",
                "claim": "Claim",
            }
        ],
        "evidence_ids": [eid],
        "orphan_ids": [],
    }


def test_execute_reviewer_records_ledger_and_ai_execution():
    clear_ledger_for_tests()
    review, provenance = execute_reviewer(
        sections=[_ok_section("Drug X reduced HbA1c [#1].")],
        supporting_count=1,
        user_id=7,
        project_id=3,
    )
    assert review["status"] == "pass"
    assert review.get("ai_execution")
    assert provenance
    ledger = recent_executions(limit=1)[0]
    assert ledger["research_job"] == "reviewer"
    assert ledger["trace_id"]
    assert ledger["evaluation"]["validation_kind"] == "deterministic"
    assert ledger["extra"]["no_llm_invocation"] is True


def test_execute_reviewer_links_parent_execution():
    clear_ledger_for_tests()
    review, _ = execute_reviewer(
        sections=[_ok_section("Unsupported claim with no marker.")],
        parent_execution_id="parent-wi-99",
    )
    assert review["status"] == "fail"
    ledger = recent_executions(limit=1)[0]
    assert ledger["parent_execution_id"] == "parent-wi-99"
