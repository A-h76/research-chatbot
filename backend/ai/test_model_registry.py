"""Tests for ModelRegistry — provider calls are mocked (no real network
calls to Claude/Gemini: neither SDK is installed nor keyed in this
environment; OpenAI mocks per the task's own instruction), with two
extra real-API smoke tests kept alongside them (call + embed) since
OPENAI_API_KEY genuinely is configured here and a real round-trip catches
things a mock can't.

Run: pytest backend/ai/test_model_registry.py -v
"""

import os
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.model_registry import ModelError, ModelRegistry, _Base


@pytest.fixture
def registry():
    return ModelRegistry()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    monkeypatch.setattr("backend.ai.model_registry.ModelRegistry._sleep", lambda self, s: None)


def _fake_openai_response(
    content="hello", prompt_tokens=10, completion_tokens=5, model="gpt-4o-mini", finish_reason="stop"
):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        model=model,
    )


# ------------------------------------------------------------ test_call_openai
def test_call_openai(registry):
    registry._openai = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: _fake_openai_response()))
    )

    result = registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert result["content"] == "hello"
    assert result["prompt_tokens"] == 10
    assert result["completion_tokens"] == 5
    assert result["total_tokens"] == 15
    assert result["model"] == "gpt-4o-mini"
    assert result["finish_reason"] == "stop"
    assert result["cost"] > 0  # gpt-4o-mini is in the pricing table


# ------------------------------------------------------------ test_call_claude
def _install_fake_anthropic(
    monkeypatch, content="claude says hi", input_tokens=8, output_tokens=4, stop_reason="end_turn"
):
    # anthropic is genuinely installed in this environment — patch the
    # real module's Client class rather than faking the whole module.
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=content)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
        model="claude-3-5-sonnet-20241022",
        stop_reason=stop_reason,
    )
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_response))
    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: fake_client)


def test_call_claude(registry, monkeypatch):
    registry._anthropic_key = "fake-key-for-test"
    _install_fake_anthropic(monkeypatch)

    result = registry.call("claude-3-5-sonnet-20241022", [{"role": "user", "content": "hi"}])
    assert result["content"] == "claude says hi"
    assert result["prompt_tokens"] == 8
    assert result["completion_tokens"] == 4
    assert result["total_tokens"] == 12
    assert result["finish_reason"] == "end_turn"


# ------------------------------------------------------------ test_call_gemini
def _install_fake_gemini(
    monkeypatch, content="gemini says hi", prompt_tokens=6, candidates_tokens=3, finish_reason="STOP"
):
    # google-genai is genuinely installed in this environment — patch the
    # real module's Client class rather than faking the whole module.
    fake_response = SimpleNamespace(
        text=content,
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=candidates_tokens,
            total_token_count=prompt_tokens + candidates_tokens,
        ),
        candidates=[SimpleNamespace(finish_reason=finish_reason)],
    )
    fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: fake_response))
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)


def test_call_gemini(registry, monkeypatch):
    registry._google_key = "fake-key-for-test"
    _install_fake_gemini(monkeypatch)

    result = registry.call("gemini-2.0-flash", [{"role": "user", "content": "hi"}])
    assert result["content"] == "gemini says hi"
    assert result["prompt_tokens"] == 6
    assert result["completion_tokens"] == 3
    assert result["total_tokens"] == 9
    assert result["finish_reason"] == "STOP"


# ------------------------------------------------------------ test_call_unsupported_model
def test_call_unsupported_model(registry):
    with pytest.raises(ModelError):
        registry.call("mystery-model-9000", [{"role": "user", "content": "hi"}])


# ------------------------------------------------------------ test_call_retry
def test_call_retry(registry):
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return _fake_openai_response(content="recovered")

    registry._openai = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=flaky)))
    result = registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert result["content"] == "recovered"
    assert calls["n"] == 3


def test_call_retry_exhausted_raises_model_error(registry):
    registry._openai = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: (_ for _ in ()).throw(RuntimeError("down for good")))
        )
    )
    with pytest.raises(ModelError) as exc_info:
        registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert exc_info.value.attempts == ModelRegistry.MAX_ATTEMPTS


def test_call_non_retryable_error_stops_immediately(registry):
    calls = {"n": 0}

    def unauthorized(**kw):
        calls["n"] += 1
        exc = RuntimeError("bad api key")
        exc.status_code = 401
        raise exc

    registry._openai = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=unauthorized)))
    with pytest.raises(ModelError):
        registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert calls["n"] == 1  # not retried


# ------------------------------------------------------------ test_embed
def test_embed(registry):
    fake_resp = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
        usage=SimpleNamespace(total_tokens=4),
    )
    registry._openai = SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kw: fake_resp))

    vector = registry.embed("hello world")
    assert vector == [0.1, 0.2, 0.3]


def test_embed_unknown_model_falls_back_to_default(registry):
    seen = {}
    fake_resp = SimpleNamespace(data=[SimpleNamespace(embedding=[0.0])], usage=SimpleNamespace(total_tokens=1))

    def create(**kw):
        seen["model"] = kw["model"]
        return fake_resp

    registry._openai = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    registry.embed("hello", model=None)
    assert seen["model"] == registry.embed_model == "text-embedding-3-small"


# ------------------------------------------------------------ cost logging
def test_call_with_logging(registry, db):
    from backend.ai.model_registry import CostLedgerEntry

    registry.db_session = db
    registry._openai = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: _fake_openai_response()))
    )

    registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}], user_id=42)

    rows = db.query(CostLedgerEntry).all()
    assert len(rows) == 1
    assert rows[0].user_id == 42
    assert rows[0].action == "chat"
    assert rows[0].model == "gpt-4o-mini"


def test_call_without_logging(registry, db):
    from backend.ai.model_registry import CostLedgerEntry

    registry.db_session = db
    registry._openai = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: _fake_openai_response()))
    )

    registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}])  # no user_id

    assert db.query(CostLedgerEntry).count() == 0


def test_call_no_logging_without_db_session(registry):
    # user_id given, but no db_session — should not raise, just skip.
    registry._openai = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: _fake_openai_response()))
    )
    result = registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}], user_id=1)
    assert result["content"] == "hello"


# ------------------------------------------------------------ streaming
def test_call_streaming(registry):
    chunks = [
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"), finish_reason=None)],
            usage=None,
            model="gpt-4o-mini",
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"), finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2, total_tokens=7),
            model="gpt-4o-mini",
        ),
    ]
    registry._openai = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: iter(chunks)))
    )

    result = registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}], stream=True)
    assert result["content"] == "Hello"
    assert result["finish_reason"] == "stop"
    assert result["prompt_tokens"] == 5
    assert result["completion_tokens"] == 2


# ------------------------------------------------------------ real API smoke tests
_openai_configured = bool(os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not _openai_configured, reason="OPENAI_API_KEY not configured")
def test_call_openai_real_round_trip():
    registry = ModelRegistry()
    result = registry.call("gpt-4o-mini", [{"role": "user", "content": "Reply with exactly: pong"}], max_tokens=10)
    assert result["content"]
    assert result["prompt_tokens"] > 0
    assert result["cost"] >= 0


@pytest.mark.skipif(not _openai_configured, reason="OPENAI_API_KEY not configured")
def test_embed_real_round_trip():
    registry = ModelRegistry()
    vector = registry.embed("hello world")
    assert isinstance(vector, list)
    assert len(vector) > 100  # text-embedding-3-small is 1536-dim
    assert all(isinstance(x, float) for x in vector[:5])


# ------------------------------------------------------------ claude/gemini: no key configured
def test_call_claude_without_api_key_raises_clear_model_error(registry):
    with pytest.raises(ModelError, match="ANTHROPIC_API_KEY"):
        registry.call("claude-3-5-sonnet-20241022", [{"role": "user", "content": "hi"}])


def test_call_gemini_without_api_key_raises_clear_model_error(registry):
    with pytest.raises(ModelError, match="GOOGLE_API_KEY"):
        registry.call("gemini-2.0-flash", [{"role": "user", "content": "hi"}])


# ------------------------------------------------------------ claude/gemini: SDK genuinely missing
# anthropic and google-genai ARE installed in this environment now — these
# force the ImportError path deterministically (sys.modules[name] = None is
# Python's own "this failed to import" sentinel) rather than relying on the
# package's absence, so the graceful-failure code path stays covered
# regardless of what's actually installed wherever this suite runs.
def test_call_claude_without_sdk_installed_raises_clear_model_error(registry, monkeypatch):
    registry._anthropic_key = "fake-key-for-this-test"
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(ModelError, match="anthropic package not installed"):
        registry.call("claude-3-5-sonnet-20241022", [{"role": "user", "content": "hi"}])


def test_call_gemini_without_sdk_installed_raises_clear_model_error(registry, monkeypatch):
    registry._google_key = "fake-key-for-this-test"
    monkeypatch.setitem(sys.modules, "google.genai", None)
    with pytest.raises(ModelError, match="google-genai package not installed"):
        registry.call("gemini-2.0-flash", [{"role": "user", "content": "hi"}])


# ------------------------------------------------------------ claude/gemini: real network, fake key
# No real ANTHROPIC_API_KEY/GOOGLE_API_KEY is configured here, so these
# can't be full success round-trips — but with both SDKs genuinely
# installed, a call with a syntactically-plausible-but-wrong key reaches
# the real provider and fails on auth for real, exercising the actual
# request-building/exception-shape code, not a mock's approximation of it.
def test_call_claude_real_network_bad_key_fails_fast_not_retried(registry):
    registry._anthropic_key = "sk-ant-fake-key-for-testing-only"

    with pytest.raises(ModelError) as exc_info:
        registry.call("claude-3-5-haiku-20241022", [{"role": "user", "content": "hi"}])
    assert exc_info.value.provider == "anthropic"
    assert exc_info.value.attempts == 1  # 401 is non-retryable — confirmed against the real SDK


def test_call_gemini_real_network_bad_key_fails_fast_not_retried(registry):
    registry._google_key = "fake-key-for-testing-only"

    with pytest.raises(ModelError) as exc_info:
        registry.call("gemini-2.0-flash", [{"role": "user", "content": "hi"}])
    assert exc_info.value.provider == "google"
    assert exc_info.value.attempts == 1  # Gemini's 400 INVALID_ARGUMENT is non-retryable too
