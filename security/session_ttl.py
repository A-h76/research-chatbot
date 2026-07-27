"""Session idle + absolute TTL helpers (PR4).

Idle: no activity for SESSION_IDLE_MINUTES → expire.
Absolute: session older than SESSION_ABSOLUTE_HOURS since login → expire.
Either limit can be disabled by setting the env value to 0.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional, Tuple

SESSION_STARTED_KEY = "_session_started_at"
SESSION_ACTIVITY_KEY = "_session_last_activity_at"


def _now(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not raw or not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def session_idle_seconds(environ: Optional[Mapping[str, str]] = None) -> int:
    env = environ if environ is not None else os.environ
    return max(0, int(env.get("SESSION_IDLE_MINUTES", "60"))) * 60


def session_absolute_seconds(environ: Optional[Mapping[str, str]] = None) -> int:
    env = environ if environ is not None else os.environ
    return max(0, int(env.get("SESSION_ABSOLUTE_HOURS", "12"))) * 3600


def mark_session_login(session: MutableMapping, *, now: Optional[datetime] = None) -> None:
    """Stamp login time + activity; mark the cookie permanent for Flask TTL."""
    ts = _now(now).isoformat()
    session[SESSION_STARTED_KEY] = ts
    session[SESSION_ACTIVITY_KEY] = ts
    try:
        session.permanent = True  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        session.modified = True  # type: ignore[attr-defined]
    except Exception:
        pass


def touch_session_activity(session: MutableMapping, *, now: Optional[datetime] = None) -> None:
    session[SESSION_ACTIVITY_KEY] = _now(now).isoformat()
    try:
        session.modified = True  # type: ignore[attr-defined]
    except Exception:
        pass


def check_session_expiry(
    session: Mapping,
    *,
    idle_seconds: int,
    absolute_seconds: int,
    now: Optional[datetime] = None,
) -> Tuple[bool, str]:
    """Return ``(expired, reason)`` where reason is ``idle`` / ``absolute`` / ````."""
    current = _now(now)
    started = _parse_ts(session.get(SESSION_STARTED_KEY))
    activity = _parse_ts(session.get(SESSION_ACTIVITY_KEY)) or started

    if absolute_seconds > 0 and started is not None:
        age = (current - started).total_seconds()
        if age > absolute_seconds:
            return True, "absolute"

    if idle_seconds > 0 and activity is not None:
        idle_for = (current - activity).total_seconds()
        if idle_for > idle_seconds:
            return True, "idle"

    return False, ""


def enforce_session_ttl(
    session: MutableMapping,
    *,
    environ: Optional[Mapping[str, str]] = None,
    now: Optional[datetime] = None,
) -> Tuple[bool, str]:
    """Bootstrap missing stamps, then check expiry.

    Returns ``(expired, reason)``. When not expired, refreshes activity.
    """
    if not session.get("user_id"):
        return False, ""

    env = environ if environ is not None else os.environ
    idle = session_idle_seconds(env)
    absolute = session_absolute_seconds(env)

    if SESSION_STARTED_KEY not in session:
        # Pre-PR4 sessions: start the clock now rather than mass-logout.
        mark_session_login(session, now=now)
        return False, ""

    expired, reason = check_session_expiry(
        session,
        idle_seconds=idle,
        absolute_seconds=absolute,
        now=now,
    )
    if expired:
        return True, reason

    touch_session_activity(session, now=now)
    return False, ""
