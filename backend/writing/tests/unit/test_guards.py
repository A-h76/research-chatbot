import pytest

from backend.writing.api.errors import WritingDomainError
from backend.writing.validation.guards import ensure_transition_allowed


def test_allowed_transition_passes():
    ensure_transition_allowed("draft", "active")


def test_invalid_transition_raises():
    with pytest.raises(WritingDomainError) as exc:
        ensure_transition_allowed("draft", "deleted")
    assert "Transition not allowed" in str(exc.value)

