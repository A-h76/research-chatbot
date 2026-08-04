"""UFTR outcome model — richer than True/False for analytics + UI Details."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class FullTextOutcome(str, Enum):
    FOUND = "FOUND"
    NO_OPEN_ACCESS = "NO_OPEN_ACCESS"
    PUBLISHER_PAYWALL = "PUBLISHER_PAYWALL"
    BOT_PROTECTION = "BOT_PROTECTION"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"


# Soft user-facing reasons (Details panel shows the enum).
USER_REASON: dict[FullTextOutcome, str] = {
    FullTextOutcome.FOUND: "Full text available.",
    FullTextOutcome.NO_OPEN_ACCESS: "No open-access version found.",
    FullTextOutcome.PUBLISHER_PAYWALL: "Publisher restrictions.",
    FullTextOutcome.BOT_PROTECTION: "Publisher restrictions.",
    FullTextOutcome.INVALID_RESPONSE: "Couldn't retrieve a usable full-text file.",
    FullTextOutcome.NETWORK_ERROR: "Couldn't reach the full-text source.",
    FullTextOutcome.TIMEOUT: "Full-text source timed out.",
}


@dataclass
class ResolutionAttempt:
    resolver: str
    outcome: FullTextOutcome
    reason: str = ""
    url: str = ""
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolver": self.resolver,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "url": (self.url or "")[:500],
            "at": self.at,
        }


@dataclass
class ResolutionResult:
    outcome: FullTextOutcome
    attempts: list[ResolutionAttempt] = field(default_factory=list)
    data: bytes | None = None
    filename: str = ""
    content_kind: str = "pdf"  # pdf | html | xml | jats (future)
    full_text_source: str = ""
    url: str = ""

    @property
    def found(self) -> bool:
        return self.outcome == FullTextOutcome.FOUND and bool(self.data)

    @property
    def user_reason(self) -> str:
        return USER_REASON.get(
            self.outcome,
            "Couldn't access the publisher's full text automatically.",
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "user_reason": self.user_reason,
            "full_text_source": self.full_text_source,
            "content_kind": self.content_kind,
            "url": (self.url or "")[:500],
            "attempts": [a.to_dict() for a in self.attempts],
            "found": self.found,
        }


def content_kind_for_bytes(data: bytes) -> str:
    if data[:4] == b"%PDF":
        return "pdf"
    head = data[:200].lstrip().lower()
    if head.startswith(b"<?xml") or b"<article" in head[:500]:
        return "xml"
    if b"<html" in head or head.startswith(b"<!doctype html"):
        return "html"
    return "unknown"
