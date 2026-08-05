"""Bite 15 — Research Workflow Engine (named steps → state → events)."""

from __future__ import annotations

import pytest

from backend.domain_events import (
    DomainEventBus,
    evidence_accepted,
    paper_imported,
    publish,
    research_decision_recorded,
    set_bus,
    writing_generated,
)
from backend.workflow.bridge import register_workflow_bridges
from backend.workflow.definitions import (
    RESEARCH_PAPER_STEPS,
    STATUS_COMPLETED,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STEP_EVIDENCE,
    STEP_IMPORT,
    STEP_REVIEW,
    STEP_SUE,
    STEP_UFTR,
    STEP_WRITING,
    WF_STATUS_COMPLETED,
    WORKFLOW_ENGINE_VERSION,
)
from backend.workflow.engine import WorkflowEngine, get_engine, set_engine


@pytest.fixture(autouse=True)
def _isolated():
    bus = DomainEventBus()
    set_bus(bus)
    eng = WorkflowEngine()
    set_engine(eng)
    # Allow re-register in this process for tests
    import backend.workflow.bridge as bridge

    bridge._BRIDGES_REGISTERED = False
    register_workflow_bridges()
    yield eng
    eng.store.clear()
    bus.clear()
    set_bus(None)
    set_engine(None)
    bridge._BRIDGES_REGISTERED = False


def test_engine_version_and_steps():
    assert WORKFLOW_ENGINE_VERSION == "1.0"
    assert RESEARCH_PAPER_STEPS == (
        "Import",
        "UFTR",
        "SUE",
        "Evidence",
        "Writing",
        "Review",
    )


def test_paper_imported_starts_inspectable_journey():
    publish(
        paper_imported(
            user_id=1, file_id=10, project_id=5, source="pubmed", already_exists=False
        )
    )
    snap = get_engine().inspect_file(1, 10)
    assert snap is not None
    assert snap["workflow_name"] == "research_paper"
    assert snap["status"] == "active"
    by_name = {s["name"]: s["status"] for s in snap["steps"]}
    assert by_name[STEP_IMPORT] == STATUS_COMPLETED
    assert by_name[STEP_UFTR] == STATUS_RUNNING
    assert snap["current_step"] == STEP_UFTR


def test_held_pdf_skips_uftr():
    publish(
        paper_imported(
            user_id=2, file_id=20, project_id=5, source="google_drive", already_exists=False
        )
    )
    snap = get_engine().inspect_file(2, 20)
    by_name = {s["name"]: s["status"] for s in snap["steps"]}
    assert by_name[STEP_UFTR] == STATUS_SKIPPED
    assert by_name[STEP_SUE] == STATUS_RUNNING


def test_uftr_and_job_advance_sue_evidence():
    eng = get_engine()
    eng.note_paper_imported(user_id=3, file_id=30, project_id=7, source="arxiv")
    eng.note_uftr_result(
        user_id=3, file_id=30, project_id=7, pdf_attached=True, analysis_queued=True
    )
    eng.note_job_outcome(
        user_id=3, file_id=30, job_type="paper_analysis", outcome="done", project_id=7
    )
    eng.note_job_outcome(
        user_id=3, file_id=30, job_type="evidence_extract", outcome="done", project_id=7
    )
    snap = eng.inspect_file(3, 30)
    by_name = {s["name"]: s["status"] for s in snap["steps"]}
    assert by_name[STEP_UFTR] == STATUS_COMPLETED
    assert by_name[STEP_SUE] == STATUS_COMPLETED
    assert by_name[STEP_EVIDENCE] == STATUS_COMPLETED
    assert by_name[STEP_WRITING] == STATUS_RUNNING


def test_writing_and_review_complete_via_domain_events():
    eng = get_engine()
    eng.note_paper_imported(user_id=4, file_id=40, project_id=9, source="pubmed")
    for step in (STEP_UFTR, STEP_SUE, STEP_EVIDENCE):
        eng.complete_step(user_id=4, file_id=40, step=step, project_id=9)
    publish(writing_generated(user_id=4, project_id=9, execution_id="w1"))
    publish(
        research_decision_recorded(
            user_id=4, decision_id=1, project_id=9, evidence_id=99, decision_type="accept"
        )
    )
    snap = eng.inspect_file(4, 40)
    by_name = {s["name"]: s["status"] for s in snap["steps"]}
    assert by_name[STEP_WRITING] == STATUS_COMPLETED
    assert by_name[STEP_REVIEW] == STATUS_COMPLETED
    assert snap["status"] == WF_STATUS_COMPLETED


def test_evidence_accepted_advances_evidence_step():
    eng = get_engine()
    eng.note_paper_imported(user_id=5, file_id=50, project_id=11, source="pubmed")
    for step in (STEP_UFTR, STEP_SUE):
        eng.complete_step(user_id=5, file_id=50, step=step, project_id=11)
    publish(evidence_accepted(user_id=5, evidence_id=3, project_id=11))
    snap = eng.inspect_file(5, 50)
    by_name = {s["name"]: s["status"] for s in snap["steps"]}
    assert by_name[STEP_EVIDENCE] == STATUS_COMPLETED


def test_job_failure_marks_step_failed():
    eng = get_engine()
    eng.note_paper_imported(user_id=6, file_id=60, project_id=1, source="pubmed")
    eng.note_job_outcome(
        user_id=6,
        file_id=60,
        job_type="paper_analysis",
        outcome="failed",
        error="boom",
        project_id=1,
    )
    snap = eng.inspect_file(6, 60)
    sue = next(s for s in snap["steps"] if s["name"] == STEP_SUE)
    assert sue["status"] == "failed"
    assert sue["error"] == "boom"
    assert snap["status"] == "failed"


def test_inspect_payload_shape():
    eng = get_engine()
    eng.ensure_research_paper(user_id=1, file_id=99, project_id=2)
    payload = eng.inspect("rw:1:file:99")
    assert payload["workflow_id"] == "rw:1:file:99"
    assert len(payload["steps"]) == 6
    assert payload["current_step"] == STEP_IMPORT
