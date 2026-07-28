from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    VALIDATION = "validation_error"
    AUTHZ_DENIED = "authz_denied"
    NOT_FOUND = "not_found"
    VERSION_CONFLICT = "version_conflict"
    RATE_LIMITED = "rate_limited"
    TRANSIENT_FAILURE = "transient_failure"
    INTERNAL = "internal_error"


class WritingDomainError(Exception):
    """Canonical writing-domain error used across services."""

    def __init__(self, code: str, detail: str = "", *, metadata: dict | None = None):
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code
        self.metadata = metadata or {}

