"""Tests for PromptRegistry against a real (in-memory SQLite) DB — the
prompt_versions table it maps onto, created via its own private Base
(see prompt_registry.py's module docstring for why that's safe here).

Run: pytest backend/ai/test_prompt_registry.py -v
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.prompt_registry import PromptRegistry, TemplateError, _Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def registry(db):
    return PromptRegistry(db)


# ------------------------------------------------------------ create_prompt
def test_create_prompt_returns_active_first_version(registry):
    row = registry.create_prompt("greeting", "says hello", "Hello, {{ name }}!")
    assert row.name == "greeting"
    assert row.version == 1
    assert row.is_active is True


def test_create_prompt_respects_explicit_default_version(registry):
    row = registry.create_prompt("greeting", "desc", "Hi {{ name }}", default_version=5)
    assert row.version == 5


def test_create_prompt_rejects_duplicate_name_and_version(registry):
    registry.create_prompt("greeting", "desc", "Hi {{ name }}")
    with pytest.raises(ValueError):
        registry.create_prompt("greeting", "desc", "Hi again {{ name }}")


# ------------------------------------------------------------ add_version
def test_add_version_auto_increments(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}")
    v2 = registry.add_version("greeting", "v2 {{ name }}")
    assert v2.version == 2
    v3 = registry.add_version("greeting", "v3 {{ name }}")
    assert v3.version == 3


def test_add_version_requires_existing_prompt(registry):
    with pytest.raises(ValueError):
        registry.add_version("nonexistent", "template")


def test_add_version_active_deactivates_previous(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}")   # active
    v2 = registry.add_version("greeting", "v2 {{ name }}", is_active=True)

    active = registry.get_active_version("greeting")
    assert active.version == 2
    assert v2.is_active is True


def test_add_version_inactive_by_default_leaves_original_active(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}")
    registry.add_version("greeting", "v2 {{ name }}")   # is_active=False
    active = registry.get_active_version("greeting")
    assert active.version == 1


# ------------------------------------------------------------ get_prompt
def test_get_prompt_renders_active_version_by_default(registry):
    registry.create_prompt("greeting", "desc", "Hello, {{ name }}!")
    text = registry.get_prompt("greeting", variables={"name": "Ada"})
    assert text == "Hello, Ada!"


def test_get_prompt_renders_specific_version(registry):
    registry.create_prompt("greeting", "desc", "v1: {{ name }}")
    registry.add_version("greeting", "v2: {{ name }}", is_active=True)

    v1_text = registry.get_prompt("greeting", version=1, variables={"name": "Ada"})
    v2_text = registry.get_prompt("greeting", version=2, variables={"name": "Ada"})
    assert v1_text == "v1: Ada"
    assert v2_text == "v2: Ada"


def test_get_prompt_no_variables_needed(registry):
    registry.create_prompt("static", "desc", "no variables here")
    assert registry.get_prompt("static") == "no variables here"


def test_get_prompt_missing_name_raises_value_error(registry):
    with pytest.raises(ValueError):
        registry.get_prompt("nonexistent")


def test_get_prompt_missing_version_raises_value_error(registry):
    registry.create_prompt("greeting", "desc", "hi")
    with pytest.raises(ValueError):
        registry.get_prompt("greeting", version=99)


def test_get_prompt_bad_template_raises_template_error(registry):
    registry.create_prompt("broken", "desc", "{{ unclosed")
    with pytest.raises(TemplateError):
        registry.get_prompt("broken")


def test_get_prompt_undefined_variable_raises_template_error(registry):
    registry.create_prompt("strict", "desc", "{{ missing.attr.chain }}")
    # Jinja2's default Undefined silently renders empty for a bare
    # variable, but attribute access on an Undefined raises — exercises
    # the wrap-into-TemplateError path with a realistic failure, not a
    # contrived syntax error.
    with pytest.raises(TemplateError):
        registry.get_prompt("strict", variables={})


# ------------------------------------------------------------ list_prompts
def test_list_prompts_returns_one_active_row_per_name(registry):
    registry.create_prompt("a", "desc", "A {{ x }}")
    registry.create_prompt("b", "desc", "B {{ x }}")
    registry.add_version("a", "A v2 {{ x }}", is_active=True)

    prompts = registry.list_prompts()
    names = sorted(p.name for p in prompts)
    assert names == ["a", "b"]
    a = next(p for p in prompts if p.name == "a")
    assert a.version == 2   # the active one, not v1


def test_list_prompts_empty_when_none_created(registry):
    assert registry.list_prompts() == []


# ------------------------------------------------------------ get_active_version
def test_get_active_version_returns_none_when_no_prompt(registry):
    assert registry.get_active_version("nonexistent") is None
