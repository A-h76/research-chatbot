import pytest

from backend.writing.api.errors import WritingDomainError
from backend.writing.services.autosave_service import (
    is_idempotent_replay,
    normalize_idempotency_key,
)


def test_normalize_idempotency_key_accepts_trimmed_value():
    assert normalize_idempotency_key("  abc-123  ") == "abc-123"


def test_normalize_idempotency_key_requires_value():
    with pytest.raises(WritingDomainError):
        normalize_idempotency_key(" ")


def test_idempotent_replay_detected():
    assert is_idempotent_replay("same-key", "same-key") is True
    assert is_idempotent_replay("same-key", "other-key") is False

