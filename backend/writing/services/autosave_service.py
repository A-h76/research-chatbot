from __future__ import annotations

from backend.writing.api.errors import ErrorCode, WritingDomainError


def normalize_idempotency_key(raw: str | None) -> str:
    key = (raw or "").strip()
    if not key:
        raise WritingDomainError(ErrorCode.VALIDATION, "idempotency_key_required")
    if len(key) > 120:
        raise WritingDomainError(ErrorCode.VALIDATION, "idempotency_key_too_long")
    return key


def is_idempotent_replay(previous_key: str | None, incoming_key: str) -> bool:
    return bool(previous_key) and previous_key == incoming_key

