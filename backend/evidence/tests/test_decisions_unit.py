"""Unit tests for Research Decisions (Phase A.2)."""

from backend.evidence.decisions import (
    DECISION_LABELS,
    decision_type_from_review_status,
    serialize_decision,
    validate_decision_payload,
)


def test_validate_accept_with_reason():
    p = validate_decision_payload(
        {"type": "ACCEPT", "evidence_id": 7, "reason": "Key finding"}
    )
    assert p["type"] == "ACCEPT"
    assert p["evidence_id"] == 7
    assert p["reason"] == "Key finding"


def test_validate_rejects_unknown_type():
    try:
        validate_decision_payload({"type": "DASHBOARD", "evidence_id": 1})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "ACCEPT" in str(exc)


def test_product_labels_are_simple():
    assert DECISION_LABELS["ACCEPT"] == "Accepted"
    assert DECISION_LABELS["REJECT"] == "Rejected"
    assert DECISION_LABELS["IMPORTANT"] == "Important"
    assert DECISION_LABELS["OPEN_QUESTION"] == "Needs Review"
    assert DECISION_LABELS["CONTRADICT"] == "Contradiction"


def test_review_status_maps_to_decision():
    assert decision_type_from_review_status("accepted") == "ACCEPT"
    assert decision_type_from_review_status("rejected") == "REJECT"


def test_serialize_decision_includes_label():
    class Row:
        id = 1
        project_id = 2
        evidence_object_id = 3
        decision_type = "ACCEPT"
        reason = "Supports hypothesis"
        reason_code = ""
        user_id = 9
        created_at = None

    dto = serialize_decision(Row(), claim_preview="Transformers outperform…")
    assert dto["label"] == "Accepted"
    assert dto["claim_preview"].startswith("Transformers")
