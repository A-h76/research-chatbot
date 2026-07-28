from backend.writing.services.version_service import (
    build_version_conflict_payload,
    next_version_number,
)


def test_build_version_conflict_payload_is_stable():
    payload = build_version_conflict_payload(7)
    assert payload == {
        "error": "version_conflict",
        "detail": "stale_document_version",
        "current_version": 7,
    }


def test_next_version_number_increments():
    assert next_version_number(3) == 4
    assert next_version_number(None) == 1

