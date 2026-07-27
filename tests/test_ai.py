"""Unit tests for the AI layer (backend/ai/) — PromptRegistry,
ModelRegistry, CostLedger — using pytest-mock's `mocker` fixture and an
in-memory SQLite DB, per this task's own instructions.

Placed literally at tests/test_ai.py as asked, despite every other test
file in this project living co-located with its module (auth/test_*.py,
backend/ai/test_*.py, etc.) — verified first that tests/conftest.py
(orphaned scaffolding for a Flask-SQLAlchemy app this project isn't —
see brain.md) doesn't interfere: its app/client/db fixtures are only
invoked if a test requests them by name, and none here do.

Deeper, provider-specific coverage (Claude/Gemini routing, retry/backoff
classification, streaming, real network round-trips against OpenAI and
real auth-failure calls to Anthropic/Google) already lives in
backend/ai/test_prompt_registry.py and backend/ai/test_model_registry.py
—48 tests between them. This file satisfies exactly what THIS task
asks for (pytest-mock style, this location, this specific list), not a
second copy of that suite.

Run: pytest tests/test_ai.py -v
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.cost_ledger import CostLedger
from backend.ai.model_registry import CostLedgerEntry, ModelError, ModelRegistry
from backend.ai.model_registry import _Base as model_base
from backend.ai.prompt_registry import PromptRegistry, TemplateError
from backend.ai.prompt_registry import _Base as prompt_base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    prompt_base.metadata.create_all(engine)
    model_base.metadata.create_all(engine)  # CostLedgerEntry, for the logging test
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def registry(db):
    return PromptRegistry(db)


@pytest.fixture
def model_registry(monkeypatch):
    # ModelRegistry() constructs a real OpenAI client, which raises at
    # construction if OPENAI_API_KEY is unset entirely (confirmed: the
    # installed openai SDK errors on a missing key, not just a bad one).
    # Every test using this fixture mocks the client anyway, so a real
    # key is never needed — this just keeps the file from silently
    # depending on whoever invokes pytest having loaded .env first.
    monkeypatch.setenv("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-test-dummy-key"))
    return ModelRegistry()


# ================================================================ PromptRegistry
# status="active" is required below wherever a test then looks the prompt
# up by name with no explicit version — PromptRegistry's own default
# status is "draft" (migration 0015's authoring lifecycle), which isn't
# servable via the no-version lookup. Deeper coverage of the state
# machine itself lives in backend/ai/test_prompt_registry.py.
def test_prompt_registry_create_prompt(registry):
    row = registry.create_prompt("summary", "summarizes text", "Summarize: {{ text }}", status="active")
    assert row.name == "summary"
    assert row.version == 1
    assert row.is_active is True


def test_prompt_registry_get_prompt(registry):
    registry.create_prompt("static", "desc", "no variables here", status="active")
    text, _version = registry.get_prompt("static")
    assert text == "no variables here"


def test_prompt_registry_add_version(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    v2 = registry.add_version("greeting", "v2 {{ name }}", is_active=True, status="active")
    assert v2.version == 2
    assert registry.get_active_version("greeting").version == 2


def test_prompt_registry_render_with_variables(registry):
    registry.create_prompt("greeting", "desc", "Hello, {{ name }}! You are {{ age }}.", status="active")
    rendered, _version = registry.get_prompt("greeting", variables={"name": "Ada", "age": 36})
    assert rendered == "Hello, Ada! You are 36."


def test_prompt_registry_handle_missing_prompt(registry):
    with pytest.raises(ValueError):
        registry.get_prompt("does-not-exist")


def test_prompt_registry_handle_bad_template(registry):
    registry.create_prompt("broken", "desc", "{{ unclosed", status="active")
    with pytest.raises(TemplateError):
        registry.get_prompt("broken")


# ================================================================ ModelRegistry
def test_model_registry_call_openai_mocked(model_registry, mocker):
    fake_choice = mocker.Mock(message=mocker.Mock(content="hello"), finish_reason="stop")
    fake_usage = mocker.Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    fake_response = mocker.Mock(choices=[fake_choice], usage=fake_usage, model="gpt-4o-mini")
    mocker.patch.object(model_registry._openai.chat.completions, "create", return_value=fake_response)

    result = model_registry._call_openai("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert result["content"] == "hello"
    assert result["prompt_tokens"] == 10
    assert result["completion_tokens"] == 5
    assert result["total_tokens"] == 15
    assert result["model"] == "gpt-4o-mini"
    assert result["finish_reason"] == "stop"


def test_model_registry_routing_dispatches_openai(model_registry, mocker):
    mock_openai = mocker.patch.object(
        model_registry,
        "_call_openai",
        return_value={
            "content": "x",
            "model": "gpt-4o-mini",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "finish_reason": "stop",
        },
    )
    mock_claude = mocker.patch.object(model_registry, "_call_claude")

    model_registry.call("gpt-4o-mini", [{"role": "user", "content": "hi"}])

    mock_openai.assert_called_once()
    mock_claude.assert_not_called()


def test_model_registry_routing_dispatches_claude(model_registry, mocker):
    mock_openai = mocker.patch.object(model_registry, "_call_openai")
    mock_claude = mocker.patch.object(
        model_registry,
        "_call_claude",
        return_value={
            "content": "y",
            "model": "claude-3-5-sonnet",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "finish_reason": "end_turn",
        },
    )

    model_registry.call("claude-3-5-sonnet", [{"role": "user", "content": "hi"}])

    mock_claude.assert_called_once()
    mock_openai.assert_not_called()


def test_model_registry_routing_unknown_prefix_raises(model_registry):
    with pytest.raises(ModelError):
        model_registry.call("unknown-model-xyz", [{"role": "user", "content": "hi"}])


# ================================================================ CostLedger
def test_cost_ledger_estimate_cost_known_model():
    ledger = CostLedger(Model=None)  # estimate_cost is pure — no DB needed
    cost = ledger.estimate_cost("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == pytest.approx(0.15 + 0.60, rel=1e-6)


def test_cost_ledger_estimate_cost_unknown_model_is_zero():
    ledger = CostLedger(Model=None)
    cost = ledger.estimate_cost("some-future-model-nobody-has-priced", 1000, 1000)
    assert cost == 0.0


def test_cost_ledger_log_persists_row(db):
    ledger = CostLedger(CostLedgerEntry)
    ledger.log(
        db,
        user_id=7,
        model="gpt-4o-mini",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        cost=0.001,
        action="chat",
    )

    rows = db.query(CostLedgerEntry).all()
    assert len(rows) == 1
    assert rows[0].user_id == 7
    assert rows[0].model == "gpt-4o-mini"
    assert rows[0].cost == 0.001
    assert rows[0].action == "chat"
