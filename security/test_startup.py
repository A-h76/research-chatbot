"""Unit tests for production secret validation and limiter storage URI."""

import pytest

from security.startup import (
    require_production_secrets,
    resolve_flask_secret_key,
    resolve_limiter_storage_uri,
)


def test_require_production_secrets_noop_outside_production():
    require_production_secrets({"FLASK_ENV": "development"}, is_production=False)


def test_require_production_secrets_rejects_dev_auto_login():
    with pytest.raises(SystemExit, match="DEV_AUTO_LOGIN"):
        require_production_secrets(
            {
                "FLASK_ENV": "production",
                "DEV_AUTO_LOGIN": "1",
                "FLASK_SECRET_KEY": "x" * 32,
                "GOOGLE_CLIENT_ID": "id",
                "GOOGLE_CLIENT_SECRET": "secret",
            },
            is_production=True,
        )


def test_require_production_secrets_missing_flask_secret():
    with pytest.raises(SystemExit, match="FLASK_SECRET_KEY"):
        require_production_secrets(
            {
                "FLASK_ENV": "production",
                "GOOGLE_CLIENT_ID": "id",
                "GOOGLE_CLIENT_SECRET": "secret",
            },
            is_production=True,
        )


def test_require_production_secrets_ok_with_minimum():
    require_production_secrets(
        {
            "FLASK_ENV": "production",
            "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
            "GOOGLE_CLIENT_ID": "id",
            "GOOGLE_CLIENT_SECRET": "secret",
            "OPENAI_API_KEY": "sk-test",
            "RESEND_API_KEY": "re_test",
            "CLAMAV_OPTIONAL": "1",
            "RATE_LIMIT_MEMORY_OK": "1",
        },
        is_production=True,
    )


def test_require_production_secrets_requires_openai():
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        require_production_secrets(
            {
                "FLASK_ENV": "production",
                "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
                "GOOGLE_CLIENT_ID": "id",
                "GOOGLE_CLIENT_SECRET": "secret",
                "RESEND_API_KEY": "re_test",
                "CLAMAV_OPTIONAL": "1",
                "RATE_LIMIT_MEMORY_OK": "1",
            },
            is_production=True,
        )


def test_require_production_secrets_requires_clamav_or_optional():
    with pytest.raises(SystemExit, match="CLAMAV"):
        require_production_secrets(
            {
                "FLASK_ENV": "production",
                "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
                "GOOGLE_CLIENT_ID": "id",
                "GOOGLE_CLIENT_SECRET": "secret",
                "OPENAI_API_KEY": "sk-test",
                "RESEND_API_KEY": "re_test",
                "RATE_LIMIT_MEMORY_OK": "1",
            },
            is_production=True,
        )


def test_require_production_secrets_clamav_enabled_ok():
    require_production_secrets(
        {
            "FLASK_ENV": "production",
            "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
            "GOOGLE_CLIENT_ID": "id",
            "GOOGLE_CLIENT_SECRET": "secret",
            "OPENAI_API_KEY": "sk-test",
            "RESEND_API_KEY": "re_test",
            "CLAMAV_ENABLED": "1",
            "RATE_LIMIT_MEMORY_OK": "1",
        },
        is_production=True,
    )


def test_require_production_secrets_requires_resend():
    with pytest.raises(SystemExit, match="RESEND_API_KEY"):
        require_production_secrets(
            {
                "FLASK_ENV": "production",
                "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
                "GOOGLE_CLIENT_ID": "id",
                "GOOGLE_CLIENT_SECRET": "secret",
                "OPENAI_API_KEY": "sk-test",
                "CLAMAV_OPTIONAL": "1",
                "RATE_LIMIT_MEMORY_OK": "1",
            },
            is_production=True,
        )


def test_require_production_secrets_r2_requires_creds():
    with pytest.raises(SystemExit, match="R2_"):
        require_production_secrets(
            {
                "FLASK_ENV": "production",
                "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
                "GOOGLE_CLIENT_ID": "id",
                "GOOGLE_CLIENT_SECRET": "secret",
                "OPENAI_API_KEY": "sk-test",
                "RESEND_API_KEY": "re_test",
                "CLAMAV_OPTIONAL": "1",
                "RATE_LIMIT_MEMORY_OK": "1",
                "STORAGE_PROVIDER": "r2",
                "R2_BUCKET": "bucket",
            },
            is_production=True,
        )


def test_require_production_secrets_missing_redis_warns_but_boots(caplog):
    """Missing Redis must not crash Gunicorn workers (availability over fail-closed)."""
    require_production_secrets(
        {
            "FLASK_ENV": "production",
            "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
            "GOOGLE_CLIENT_ID": "id",
            "GOOGLE_CLIENT_SECRET": "secret",
            "OPENAI_API_KEY": "sk-test",
            "RESEND_API_KEY": "re_test",
            "CLAMAV_OPTIONAL": "1",
        },
        is_production=True,
    )
    assert "REDIS_URL unset" in caplog.text
    assert "memory://" in caplog.text


def test_require_production_secrets_ok_with_redis_url():
    require_production_secrets(
        {
            "FLASK_ENV": "production",
            "FLASK_SECRET_KEY": "prod-secret-key-at-least-32-chars!!",
            "GOOGLE_CLIENT_ID": "id",
            "GOOGLE_CLIENT_SECRET": "secret",
            "OPENAI_API_KEY": "sk-test",
            "RESEND_API_KEY": "re_test",
            "CLAMAV_OPTIONAL": "1",
            "REDIS_URL": "redis://localhost:6379/0",
        },
        is_production=True,
    )


def test_resolve_flask_secret_key_ephemeral_in_dev():
    key = resolve_flask_secret_key({}, is_production=False)
    assert len(key) >= 32


def test_resolve_flask_secret_key_refuses_ephemeral_in_prod():
    with pytest.raises(SystemExit, match="FLASK_SECRET_KEY"):
        resolve_flask_secret_key({}, is_production=True)


def test_resolve_limiter_storage_uri_memory_when_unset():
    assert resolve_limiter_storage_uri("", is_production=False) == "memory://"


def test_resolve_limiter_storage_uri_prod_without_redis_warns_but_memory(caplog):
    """Allowed only after RATE_LIMIT_MEMORY_OK ack at require_production_secrets."""
    uri = resolve_limiter_storage_uri("", is_production=True)
    assert uri == "memory://"


def test_resolve_limiter_storage_uri_prod_unreachable_falls_back(mocker):
    mocker.patch(
        "redis.from_url",
        side_effect=ConnectionError("refused"),
    )
    assert (
        resolve_limiter_storage_uri("redis://localhost:6379/0", is_production=True)
        == "memory://"
    )


def test_resolve_limiter_storage_uri_dev_unreachable_falls_back(mocker):
    mocker.patch(
        "redis.from_url",
        side_effect=ConnectionError("refused"),
    )
    assert (
        resolve_limiter_storage_uri("redis://localhost:6379/0", is_production=False)
        == "memory://"
    )
