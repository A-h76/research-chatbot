"""Tests for optional Sentry init (V1 #20)."""

from __future__ import annotations

import pytest

from security.sentry_init import init_sentry


def test_init_sentry_skips_without_dsn():
    assert init_sentry({}) is False


def test_init_sentry_skips_blank_dsn():
    assert init_sentry({"SENTRY_DSN": "  "}) is False


def test_init_sentry_calls_sdk_when_dsn_set(mocker):
    pytest.importorskip("sentry_sdk")
    mock_init = mocker.patch("sentry_sdk.init")
    mocker.patch("sentry_sdk.integrations.flask.FlaskIntegration")

    ok = init_sentry(
        {
            "SENTRY_DSN": "https://key@o0.ingest.sentry.io/1",
            "SENTRY_ENVIRONMENT": "test",
            "SENTRY_TRACES_SAMPLE_RATE": "0.1",
        }
    )
    assert ok is True
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"].startswith("https://")
    assert kwargs["environment"] == "test"
    assert kwargs["traces_sample_rate"] == 0.1
    assert kwargs["send_default_pii"] is False


def test_init_sentry_init_failure_returns_false(mocker):
    pytest.importorskip("sentry_sdk")
    mocker.patch("sentry_sdk.init", side_effect=RuntimeError("boom"))
    mocker.patch("sentry_sdk.integrations.flask.FlaskIntegration")
    assert init_sentry({"SENTRY_DSN": "https://key@o0.ingest.sentry.io/1"}) is False
