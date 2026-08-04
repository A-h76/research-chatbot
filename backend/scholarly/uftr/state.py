"""UFTR state on UserFile.fulltext_json — provenance + retry policy."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.scholarly.uftr.outcomes import (
    USER_REASON,
    FullTextOutcome,
    ResolutionAttempt,
    ResolutionResult,
)

logger = logging.getLogger(__name__)

FULLTEXT_NEEDED_OUTCOMES = frozenset(
    {
        FullTextOutcome.NO_OPEN_ACCESS,
        FullTextOutcome.PUBLISHER_PAYWALL,
        FullTextOutcome.BOT_PROTECTION,
        FullTextOutcome.INVALID_RESPONSE,
        FullTextOutcome.NETWORK_ERROR,
        FullTextOutcome.TIMEOUT,
    }
)

AUTO_RETRY_DAYS = 7
MAX_STORED_ATTEMPTS = 40


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_fulltext_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if not raw or not isinstance(raw, str):
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def dumps_fulltext(data: dict[str, Any]) -> str:
    try:
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        return "{}"


def fulltext_payload(uf: Any) -> dict[str, Any] | None:
    """Public full-text resolution summary for API/UI (or None if empty)."""
    state = parse_fulltext_json(getattr(uf, "fulltext_json", None))
    if not state:
        return None
    outcome_s = (state.get("outcome") or "").strip()
    try:
        outcome = FullTextOutcome(outcome_s) if outcome_s else None
    except ValueError:
        outcome = None
    user_reason = state.get("user_reason") or (
        USER_REASON.get(outcome, "") if outcome else ""
    )
    return {
        "outcome": outcome_s or None,
        "user_reason": user_reason or None,
        "full_text_source": state.get("full_text_source") or "",
        "content_kind": state.get("content_kind") or "",
        "url": (state.get("url") or "")[:500],
        "last_attempt_at": state.get("last_attempt_at"),
        "resolving": bool(state.get("resolving")),
        "attempts": (state.get("fetch_attempts") or state.get("attempts") or [])[-12:],
        "found": outcome == FullTextOutcome.FOUND,
    }


def apply_resolution_to_file(
    uf: Any,
    result: ResolutionResult,
    *,
    resolving: bool = False,
) -> dict[str, Any]:
    """Merge a ResolutionResult into uf.fulltext_json (in-memory; caller commits)."""
    prev = parse_fulltext_json(getattr(uf, "fulltext_json", None))
    attempts = list(prev.get("fetch_attempts") or prev.get("attempts") or [])
    for a in result.attempts:
        attempts.append(a.to_dict() if isinstance(a, ResolutionAttempt) else a)
    if len(attempts) > MAX_STORED_ATTEMPTS:
        attempts = attempts[-MAX_STORED_ATTEMPTS:]

    state = {
        "outcome": result.outcome.value,
        "user_reason": result.user_reason,
        "full_text_source": result.full_text_source or prev.get("full_text_source") or "",
        "content_kind": result.content_kind or "pdf",
        "url": (result.url or "")[:500],
        "last_attempt_at": _now_iso(),
        "resolving": bool(resolving),
        "fetch_attempts": attempts,
        "manual_attach_count": int(prev.get("manual_attach_count") or 0),
    }
    if hasattr(uf, "fulltext_json"):
        uf.fulltext_json = dumps_fulltext(state)
    return state


def mark_resolving(uf: Any, *, on: bool = True) -> None:
    state = parse_fulltext_json(getattr(uf, "fulltext_json", None))
    state["resolving"] = bool(on)
    if on:
        state["last_attempt_at"] = _now_iso()
    if hasattr(uf, "fulltext_json"):
        uf.fulltext_json = dumps_fulltext(state)


def record_manual_attach(uf: Any, *, source: str = "manual") -> None:
    state = parse_fulltext_json(getattr(uf, "fulltext_json", None))
    state["outcome"] = FullTextOutcome.FOUND.value
    state["user_reason"] = USER_REASON[FullTextOutcome.FOUND]
    state["full_text_source"] = source
    state["content_kind"] = "pdf"
    state["resolving"] = False
    state["last_attempt_at"] = _now_iso()
    state["manual_attach_count"] = int(state.get("manual_attach_count") or 0) + 1
    attempts = list(state.get("fetch_attempts") or [])
    attempts.append(
        {
            "resolver": source,
            "outcome": FullTextOutcome.FOUND.value,
            "reason": "manual_attach",
            "url": "",
            "at": _now_iso(),
        }
    )
    state["fetch_attempts"] = attempts[-MAX_STORED_ATTEMPTS:]
    if hasattr(uf, "fulltext_json"):
        uf.fulltext_json = dumps_fulltext(state)


def should_auto_retry(
    uf: Any,
    *,
    now: datetime | None = None,
    force: bool = False,
    min_days: int = AUTO_RETRY_DAYS,
) -> bool:
    """True when event-driven retry should run UFTR again.

    Constraints: no PDF yet; not currently resolving; last attempt older than
    min_days (or never attempted); force bypasses the age gate.
    """
    from backend.library.readiness import has_pdf

    if has_pdf(uf):
        return False
    if force:
        return True

    state = parse_fulltext_json(getattr(uf, "fulltext_json", None))
    if state.get("resolving"):
        return False

    last = state.get("last_attempt_at")
    if not last:
        # Never attempted — allow (Discover may have set outcome without stamp)
        return True

    try:
        ts = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        return True

    ref = now or datetime.now(timezone.utc)
    return ref - ts >= timedelta(days=max(0, int(min_days)))


def lifecycle_label(uf: Any) -> str:
    """Human lifecycle label for UI (maps onto readiness)."""
    from backend.library.readiness import has_pdf, research_readiness

    state = parse_fulltext_json(getattr(uf, "fulltext_json", None))
    if state.get("resolving") and not has_pdf(uf):
        return "Full Text Resolving"
    if not has_pdf(uf):
        return "Full Text Needed" if state.get("outcome") else "Metadata Ready"
    ready = research_readiness(uf)
    if ready == "pdf_attached":
        return "Analyzing"
    if ready in ("analysed", "indexed"):
        return "Evidence Ready"
    if ready == "research_ready":
        return "Research Ready"
    return "Research Ready"
