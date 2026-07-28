from __future__ import annotations

from backend.writing.api.errors import ErrorCode, WritingDomainError

VALID_EDITOR_KINDS = {"markdown", "richtext"}
VALID_LIST_STATES = {"draft", "active", "archived", "deleted"}


def normalize_editor_kind(raw: str | None) -> str:
    kind = (raw or "markdown").strip().lower()
    return kind if kind in VALID_EDITOR_KINDS else "markdown"


def normalize_status_filter(raw: str | None) -> str | None:
    if raw is None:
        return None
    status = str(raw).strip().lower()
    if status not in VALID_LIST_STATES:
        raise WritingDomainError(ErrorCode.VALIDATION, "invalid_status_filter")
    return status

