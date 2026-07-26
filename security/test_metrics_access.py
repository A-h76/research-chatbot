"""Tests for /metrics access policy (PR2)."""

from security.metrics_access import check_metrics_access, is_loopback_remote


def test_loopback_detection():
    assert is_loopback_remote("127.0.0.1")
    assert is_loopback_remote("::1")
    assert not is_loopback_remote("8.8.8.8")
    assert not is_loopback_remote(None)


def test_token_required_when_set():
    env = {"METRICS_TOKEN": "s3cret"}
    ok, reason = check_metrics_access(
        authorization="Bearer s3cret",
        remote_addr="8.8.8.8",
        environ=env,
    )
    assert ok and reason == "token"

    ok, reason = check_metrics_access(
        authorization="Bearer wrong",
        remote_addr="127.0.0.1",
        environ=env,
    )
    assert not ok and reason == "bad_or_missing_token"

    ok, reason = check_metrics_access(
        authorization=None,
        remote_addr="127.0.0.1",
        environ=env,
    )
    assert not ok


def test_loopback_when_no_token():
    ok, reason = check_metrics_access(
        authorization=None,
        remote_addr="127.0.0.1",
        environ={},
    )
    assert ok and reason == "loopback"


def test_remote_denied_without_token_or_allow():
    ok, reason = check_metrics_access(
        authorization=None,
        remote_addr="10.0.0.5",
        environ={},
    )
    assert not ok and reason == "denied"


def test_allow_unauthenticated_escape_hatch():
    ok, reason = check_metrics_access(
        authorization=None,
        remote_addr="10.0.0.5",
        environ={"METRICS_ALLOW_UNAUTHENTICATED": "1"},
    )
    assert ok and reason == "allow_unauthenticated"
