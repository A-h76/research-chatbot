"""Tests for ModelRouter — pure config + in-memory state, no DB, no
mocking needed beyond monkeypatching env vars.

Run: pytest backend/ai/test_model_router.py -v
"""
import pytest

from backend.ai.model_router import ModelRouter


@pytest.fixture
def router():
    return ModelRouter({
        "chat": "gpt-4o",
        "paper_analysis": "gpt-4o",
        "embedding": "text-embedding-3-small",
        "_default": "gpt-4o",
    })


# ------------------------------------------------------------ precedence
def test_returns_dict_default_when_nothing_else_set(router):
    assert router.get_model_for_task("paper_analysis") == "gpt-4o"


def test_falls_back_to_underscore_default_for_unlisted_task(router):
    assert router.get_model_for_task("some_future_task") == "gpt-4o"


def test_env_var_overrides_dict_default(router, monkeypatch):
    monkeypatch.setenv("PAPER_ANALYSIS_MODEL", "gpt-4o-mini")
    assert router.get_model_for_task("paper_analysis") == "gpt-4o-mini"


def test_env_var_name_is_task_name_upper_plus_model_suffix(router, monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
    assert router.get_model_for_task("embedding") == "text-embedding-3-large"


def test_empty_env_var_is_treated_as_unset(router, monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "")
    assert router.get_model_for_task("chat") == "gpt-4o"


def test_set_model_for_task_overrides_dict_default(router):
    router.set_model_for_task("chat", "claude-3-5-sonnet")
    assert router.get_model_for_task("chat") == "claude-3-5-sonnet"


def test_set_model_for_task_overrides_env_var_too(router, monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "gpt-4o-mini")
    router.set_model_for_task("chat", "claude-3-5-sonnet")
    assert router.get_model_for_task("chat") == "claude-3-5-sonnet"


def test_override_on_a_task_not_in_defaults_still_works(router):
    router.set_model_for_task("brand_new_task", "gpt-4o-mini")
    assert router.get_model_for_task("brand_new_task") == "gpt-4o-mini"


# ------------------------------------------------------------ clear_override
def test_clear_override_reverts_to_env_var(router, monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "gpt-4o-mini")
    router.set_model_for_task("chat", "claude-3-5-sonnet")
    router.clear_override("chat")
    assert router.get_model_for_task("chat") == "gpt-4o-mini"


def test_clear_override_reverts_to_dict_default_when_no_env_var(router):
    router.set_model_for_task("chat", "claude-3-5-sonnet")
    router.clear_override("chat")
    assert router.get_model_for_task("chat") == "gpt-4o"


def test_clear_override_is_a_noop_when_nothing_overridden(router):
    router.clear_override("chat")   # must not raise
    assert router.get_model_for_task("chat") == "gpt-4o"


# ------------------------------------------------------------ instance isolation
def test_overrides_are_per_instance_not_shared(router):
    # Two OS processes (server.py, worker.py) each get their own
    # ModelRouter — an override set on one must never leak to another.
    other = ModelRouter({"_default": "gpt-4o"})
    router.set_model_for_task("chat", "claude-3-5-sonnet")
    assert other.get_model_for_task("chat") == "gpt-4o"
