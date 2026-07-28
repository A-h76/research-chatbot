"""Evidence Layer domain errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    VALIDATION = "validation_error"
    AUTHZ_DENIED = "authz_denied"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    NOT_READY = "not_research_ready"
    INTERNAL = "internal_error"


class EvidenceDomainError(Exception):
    def __init__(self, code: str, detail: str = "", *, metadata: dict | None = None):
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code
        self.metadata = metadata or {}
