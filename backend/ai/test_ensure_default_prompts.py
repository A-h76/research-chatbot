"""ensure_default_prompts must seed everything PromptBuilder needs at request time."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.prompt_registry import PromptRegistry, _Base
from backend.ai.prompts import ensure_default_prompts
from backend.ai.system_prompt import DEFAULT_SYSTEM_PROMPT, SystemPromptManager


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_ensure_default_prompts_seeds_system_prompt_when_missing(db):
    registry = PromptRegistry(db)
    assert registry.get_active_version(SystemPromptManager.NAME) is None

    ensure_default_prompts(db)

    assert SystemPromptManager(registry).get_active_prompt() == DEFAULT_SYSTEM_PROMPT


def test_ensure_default_prompts_does_not_overwrite_custom_system_prompt(db):
    SystemPromptManager(PromptRegistry(db)).set_active_prompt("Custom operator prompt.")
    ensure_default_prompts(db)
    assert SystemPromptManager(PromptRegistry(db)).get_active_prompt() == "Custom operator prompt."
