"""Unit tests for session idle/absolute TTL (PR4)."""

from datetime import datetime, timedelta, timezone

from security.session_ttl import (
    SESSION_ACTIVITY_KEY,
    SESSION_STARTED_KEY,
    check_session_expiry,
    enforce_session_ttl,
    mark_session_login,
)


def test_mark_session_login_stamps_keys():
    session = {}
    mark_session_login(session, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert SESSION_STARTED_KEY in session
    assert SESSION_ACTIVITY_KEY in session
    assert session[SESSION_STARTED_KEY] == session[SESSION_ACTIVITY_KEY]


def test_idle_expiry():
    started = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    session = {
        SESSION_STARTED_KEY: started.isoformat(),
        SESSION_ACTIVITY_KEY: started.isoformat(),
    }
    expired, reason = check_session_expiry(
        session,
        idle_seconds=60,
        absolute_seconds=3600,
        now=started + timedelta(seconds=61),
    )
    assert expired and reason == "idle"


def test_absolute_expiry():
    started = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    session = {
        SESSION_STARTED_KEY: started.isoformat(),
        SESSION_ACTIVITY_KEY: (started + timedelta(hours=11)).isoformat(),
    }
    expired, reason = check_session_expiry(
        session,
        idle_seconds=24 * 3600,
        absolute_seconds=12 * 3600,
        now=started + timedelta(hours=12, seconds=1),
    )
    assert expired and reason == "absolute"


def test_enforce_bootstraps_legacy_session():
    session = {"user_id": 1}
    expired, reason = enforce_session_ttl(
        session,
        environ={"SESSION_IDLE_MINUTES": "60", "SESSION_ABSOLUTE_HOURS": "12"},
    )
    assert not expired
    assert SESSION_STARTED_KEY in session


def test_enforce_clears_via_caller_on_expiry():
    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = {
        "user_id": 1,
        SESSION_STARTED_KEY: started.isoformat(),
        SESSION_ACTIVITY_KEY: started.isoformat(),
    }
    expired, reason = enforce_session_ttl(
        session,
        environ={"SESSION_IDLE_MINUTES": "1", "SESSION_ABSOLUTE_HOURS": "12"},
        now=started + timedelta(minutes=2),
    )
    assert expired and reason == "idle"
