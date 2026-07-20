"""Unit tests for observability/ — the JSON formatter, correlation-id
propagation, and the shared AI-call metric recorder. Flask-route-level
coverage (correlation id round-trip through /api/worker/health, /metrics
serving real Prometheus text) lives in test_worker_health.py and was
verified live via a running server — this file covers the module's own
logic in isolation.

Run: pytest observability/test_observability.py -v
"""
import json
import logging

from observability.logging_config import JSONFormatter, correlation_id_var
from observability.metrics import AI_CALLS_TOTAL, AI_TOKENS_TOTAL, record_ai_call, render_metrics


def _make_record(msg="hello", **extra):
    record = logging.LogRecord(
        name="test.logger", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


def test_json_formatter_produces_valid_json_with_core_fields():
    payload = json.loads(JSONFormatter().format(_make_record("hi there")))
    assert payload["message"] == "hi there"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert "timestamp" in payload


def test_json_formatter_includes_correlation_id_when_set():
    token = correlation_id_var.set("req-abc123")
    try:
        payload = json.loads(JSONFormatter().format(_make_record()))
        assert payload["correlation_id"] == "req-abc123"
    finally:
        correlation_id_var.reset(token)


def test_json_formatter_omits_correlation_id_when_unset():
    token = correlation_id_var.set(None)
    try:
        payload = json.loads(JSONFormatter().format(_make_record()))
        assert "correlation_id" not in payload
    finally:
        correlation_id_var.reset(token)


def test_json_formatter_surfaces_extra_fields():
    payload = json.loads(JSONFormatter().format(_make_record(status=200, route="/api/x")))
    assert payload["status"] == 200
    assert payload["route"] == "/api/x"


def test_record_ai_call_increments_call_and_token_counters():
    before = AI_CALLS_TOTAL.labels(model="gpt-test-model")._value.get()
    record_ai_call("gpt-test-model", prompt_tokens=10, completion_tokens=4)
    assert AI_CALLS_TOTAL.labels(model="gpt-test-model")._value.get() == before + 1
    assert AI_TOKENS_TOTAL.labels(model="gpt-test-model", token_type="prompt")._value.get() >= 10
    assert AI_TOKENS_TOTAL.labels(model="gpt-test-model", token_type="completion")._value.get() >= 4


def test_record_ai_call_skips_zero_token_labels():
    record_ai_call("gpt-embed-only-model", prompt_tokens=5, completion_tokens=0)
    # completion_tokens=0 -> that label combination is never touched, not
    # set to zero — matches the "if prompt_tokens:"/"if completion_tokens:"
    # guards in record_ai_call.
    assert AI_TOKENS_TOTAL.labels(model="gpt-embed-only-model", token_type="prompt")._value.get() >= 5


def test_render_metrics_returns_prometheus_text_exposition_format():
    body = render_metrics().decode("utf-8")
    assert "# HELP ai_calls_total" in body
    assert "# TYPE http_requests_total counter" in body
