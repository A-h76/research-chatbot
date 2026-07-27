"""PR1 integration: rate-limit handler + chat decorator presence."""

import pytest


@pytest.fixture(scope="module")
def app_module():
    import server

    return server


def test_limiter_storage_is_configured(app_module):
    assert app_module._LIMITER_STORAGE
    assert app_module._LIMITER_STORAGE == "memory://" or "redis" in app_module._LIMITER_STORAGE


def test_chat_route_has_rate_limit_decorator(app_module):
    view = app_module.app.view_functions.get("chat")
    assert view is not None
    assert hasattr(view, "__wrapped__")


def test_rate_limit_exceeded_handler_returns_429(app_module, mocker):
    from flask_limiter._limits import RuntimeLimit
    from flask_limiter.errors import RateLimitExceeded
    from limits import parse

    logged = mocker.patch.object(app_module, "log_security_event")
    limit = RuntimeLimit(parse("1 per hour"), key_func=lambda: "test", scope="test")
    exc = RateLimitExceeded(limit)

    with app_module.app.test_request_context("/api/chat", method="POST"):
        resp, status = app_module._rate_limit_exceeded(exc)

    assert status == 429
    body = resp.get_json()
    assert body["error"] == "rate_limit_exceeded"
    logged.assert_called()
    assert logged.call_args[0][0] == "rate_limit_exceeded"
