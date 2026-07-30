from backend.workflow.events import WORKFLOW_EVENTS, validate_workflow_event


def test_catalog_includes_phase_a_events():
    for name in (
        "project_created",
        "evidence_accepted",
        "draft_generated",
        "export_completed",
        "workflow_abandoned",
        "analysis_view_opened",
    ):
        assert name in WORKFLOW_EVENTS


def test_validate_strips_sensitive_meta():
    p = validate_workflow_event(
        {
            "event": "draft_generated",
            "project_id": 3,
            "meta": {"section_type": "literature_review", "quote": "secret", "claim": "nope"},
        }
    )
    assert p["event"] == "draft_generated"
    assert p["meta"]["section_type"] == "literature_review"
    assert "quote" not in p["meta"]
    assert "claim" not in p["meta"]


def test_validate_rejects_unknown_event():
    try:
        validate_workflow_event({"event": "decision_dashboard_opened"})
        assert False
    except ValueError as exc:
        assert "unknown" in str(exc)
