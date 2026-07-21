"""Tests for SystemPromptManager against a real (in-memory SQLite) DB —
same pattern as backend/ai/test_prompt_registry.py, since this class is a
thin wrapper over PromptRegistry, not a separate storage layer.

Run: pytest backend/ai/test_system_prompt.py -v
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.prompt_registry import PromptRegistry, _Base
from backend.ai.system_prompt import SystemPromptManager, DEFAULT_SYSTEM_PROMPT


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def manager(db):
    return SystemPromptManager(PromptRegistry(db))


def test_get_active_prompt_raises_when_unseeded(manager):
    # No fallback baked into this class — same as PromptRegistry.get_prompt()
    # itself; seeding (seed.py's seed_system_prompt()) is what's responsible
    # for there being something to fetch, not this method silently
    # inventing a default.
    with pytest.raises(ValueError):
        manager.get_active_prompt()


def test_set_active_prompt_creates_first_version_as_active(manager):
    manager.set_active_prompt("Custom system prompt.")
    assert manager.get_active_prompt() == "Custom system prompt."


def test_set_active_prompt_is_immediately_active_not_draft(manager, db):
    # The whole point of this class: callers never see PromptRegistry's
    # own draft-by-default behavior (migration 0015's authoring lifecycle).
    manager.set_active_prompt("v1")
    row = PromptRegistry(db).get_active_version(SystemPromptManager.NAME)
    assert row.status == "active"
    assert row.is_active is True


def test_set_active_prompt_adds_new_version_and_deactivates_previous(manager):
    manager.set_active_prompt("v1")
    manager.set_active_prompt("v2")
    assert manager.get_active_prompt() == "v2"
    assert manager.list_prompts() == ["v1", "v2"]


def test_list_prompts_returns_full_history_oldest_first(manager):
    manager.set_active_prompt("first")
    manager.set_active_prompt("second")
    manager.set_active_prompt("third")
    assert manager.list_prompts() == ["first", "second", "third"]


def test_list_prompts_empty_when_unseeded(manager):
    assert manager.list_prompts() == []


def test_default_system_prompt_is_a_real_sentence_not_a_placeholder(manager):
    # Guards against ever shipping a literal "..."-truncated string —
    # this constant is meant to be the actual seeded content.
    assert len(DEFAULT_SYSTEM_PROMPT) > 100
    assert "..." not in DEFAULT_SYSTEM_PROMPT
