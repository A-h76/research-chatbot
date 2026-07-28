from __future__ import annotations

from backend.writing.api.errors import ErrorCode, WritingDomainError

DOC_STATES = ("draft", "active", "archived", "deleted", "purged")

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active"},
    "active": {"archived"},
    "archived": {"active", "deleted"},
    "deleted": {"purged"},
    "purged": set(),
}


def ensure_transition_allowed(current: str, target: str) -> None:
    """Raise a typed domain error when lifecycle transition is invalid."""
    if current not in _ALLOWED_TRANSITIONS:
        raise WritingDomainError(
            ErrorCode.VALIDATION,
            f"Unknown current state: {current}",
        )
    if target not in DOC_STATES:
        raise WritingDomainError(
            ErrorCode.VALIDATION,
            f"Unknown target state: {target}",
        )
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise WritingDomainError(
            ErrorCode.VALIDATION,
            f"Transition not allowed: {current} -> {target}",
            metadata={"current": current, "target": target},
        )

