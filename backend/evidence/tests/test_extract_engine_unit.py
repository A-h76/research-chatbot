"""Bite 5 — ACR-wrapped evidence extraction + ledger."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.ai.ai_ledger import clear_ledger_for_tests, recent_executions
from backend.evidence.services.extract_engine import execute_evidence_extraction


def test_execute_evidence_extraction_records_ledger(monkeypatch):
    clear_ledger_for_tests()

    def _fake_run(*_args, **_kwargs):
        return {
            "status": "succeeded",
            "reason": "extracted",
            "objects_created": 3,
            "run_id": 99,
        }

    monkeypatch.setattr(
        "backend.evidence.services.extract_engine.run_evidence_extraction",
        _fake_run,
    )

    result = execute_evidence_extraction(
        MagicMock(),
        user_id=1,
        project_id=2,
        file_id=3,
        UserFile=object,
        AnalysisPipelineResult=object,
        EvidenceObject=object,
        EvidenceExtractionRun=object,
        load_analysis_result=lambda *a, **k: None,
    )
    assert result["objects_created"] == 3
    assert result.get("ai_execution")
    ledger = recent_executions(limit=1)[0]
    assert ledger["research_job"] == "evidence_extraction"
    assert ledger["trace_id"]
    assert ledger["evaluation"]["validation_kind"] == "deterministic"
    assert ledger["extra"]["no_llm_invocation"] is True
    assert ledger["status"] == "succeeded"


def test_resolve_evidence_extract_uses_lowest_cost():
    from backend.ai.capability_router.evidence_extract_resolve import resolve_evidence_extract_execution

    plan = resolve_evidence_extract_execution()
    assert plan.research_job.value == "evidence_extraction"
    assert plan.capability.value == "structured_extraction"
    assert plan.execution_policy.value == "lowest_cost"
