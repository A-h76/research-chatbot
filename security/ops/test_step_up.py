"""Unit tests for account-delete step-up (#16)."""

from __future__ import annotations

from security.ops.step_up import authorize_account_delete


def test_password_account_requires_confirm_and_password():
    ok, reason = authorize_account_delete(
        has_password=True,
        user_email="a@b.com",
        body={"password": "secret"},
        password_matches=True,
    )
    assert ok is False
    assert reason == "confirm_required"

    ok, reason = authorize_account_delete(
        has_password=True,
        user_email="a@b.com",
        body={"confirm": "DELETE"},
        password_matches=True,
    )
    assert ok is False
    assert reason == "password_required"


def test_password_account_rejects_wrong_password():
    ok, reason = authorize_account_delete(
        has_password=True,
        user_email="a@b.com",
        body={"confirm": "DELETE", "password": "nope"},
        password_matches=False,
    )
    assert ok is False
    assert reason == "wrong_password"


def test_password_account_accepts_correct_password():
    ok, reason = authorize_account_delete(
        has_password=True,
        user_email="a@b.com",
        body={"confirm": "DELETE", "password": "correct-horse"},
        password_matches=True,
    )
    assert ok is True
    assert reason == "ok"


def test_oauth_account_requires_matching_email():
    ok, reason = authorize_account_delete(
        has_password=False,
        user_email="user@uni.edu",
        body={"confirm": "DELETE"},
    )
    assert ok is False
    assert reason == "email_required"

    ok, reason = authorize_account_delete(
        has_password=False,
        user_email="user@uni.edu",
        body={"confirm": "DELETE", "email": "other@uni.edu"},
    )
    assert ok is False
    assert reason == "email_mismatch"

    ok, reason = authorize_account_delete(
        has_password=False,
        user_email="User@Uni.Edu",
        body={"confirm": "DELETE", "email": "user@uni.edu"},
    )
    assert ok is True
    assert reason == "ok"
