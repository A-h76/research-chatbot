"""Tests for PromptRegistry against a real (in-memory SQLite) DB — the
prompt_versions table it maps onto, created via its own private Base
(see prompt_registry.py's module docstring for why that's safe here).

Run: pytest backend/ai/test_prompt_registry.py -v
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.prompt_registry import PromptRegistry, TemplateError, PromptVersion, _Base


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
def test_create_prompt_defaults_to_draft_and_inactive(registry):
    row = registry.create_prompt("greeting", "says hello", "Hello, {{ name }}!")
    assert row.status == "draft"
    assert row.is_active is False


def test_create_prompt_status_active_returns_active_first_version(registry):
    row = registry.create_prompt("greeting", "says hello", "Hello, {{ name }}!", status="active")
    assert row.name == "greeting"
    assert row.version == 1
    assert row.status == "active"
    assert row.is_active is True


def test_create_prompt_respects_explicit_default_version(registry):
    row = registry.create_prompt("greeting", "desc", "Hi {{ name }}", default_version=5)
    assert row.version == 5


def test_create_prompt_rejects_duplicate_name_and_version(registry):
    registry.create_prompt("greeting", "desc", "Hi {{ name }}")
    with pytest.raises(ValueError):
        registry.create_prompt("greeting", "desc", "Hi again {{ name }}")


def test_create_prompt_stores_all_new_fields(registry):
    row = registry.create_prompt(
        "greeting", "a friendly opener", "Hi {{ name }}", status="active",
        category="onboarding", examples=[{"input": "Ada", "output": "Hi Ada"}],
        expected_output_type="markdown", author_user_id=42,
    )
    assert row.description == "a friendly opener"
    assert row.category == "onboarding"
    assert row.expected_output_type == "markdown"
    assert row.author_user_id == 42
    import json
    assert json.loads(row.examples) == [{"input": "Ada", "output": "Hi Ada"}]


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


def test_add_version_defaults_to_draft_and_inactive(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    v2 = registry.add_version("greeting", "v2 {{ name }}")
    assert v2.status == "draft"
    assert v2.is_active is False


def test_add_version_active_deactivates_previous(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    v2 = registry.add_version("greeting", "v2 {{ name }}", is_active=True, status="active")

    active = registry.get_active_version("greeting")
    assert active.version == 2
    assert v2.is_active is True


def test_add_version_inactive_by_default_leaves_original_active(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    registry.add_version("greeting", "v2 {{ name }}")   # is_active=False, status="draft" default
    active = registry.get_active_version("greeting")
    assert active.version == 1


def test_add_version_is_active_without_status_active_raises(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    with pytest.raises(ValueError):
        registry.add_version("greeting", "v2 {{ name }}", is_active=True)   # status defaults to "draft"


def test_add_version_is_active_with_status_draft_raises(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    with pytest.raises(ValueError):
        registry.add_version("greeting", "v2 {{ name }}", is_active=True, status="draft")


def test_add_version_is_active_with_status_archived_raises(registry):
    registry.create_prompt("greeting", "desc", "v1 {{ name }}", status="active")
    with pytest.raises(ValueError):
        registry.add_version("greeting", "v2 {{ name }}", is_active=True, status="archived")


# ------------------------------------------------------------ get_prompt
def test_get_prompt_renders_active_version_by_default(registry):
    registry.create_prompt("greeting", "desc", "Hello, {{ name }}!", status="active")
    text, row = registry.get_prompt("greeting", variables={"name": "Ada"})
    assert text == "Hello, Ada!"
    assert row.name == "greeting"
    assert row.version == 1


def test_get_prompt_returns_the_resolved_version_row(registry):
    registry.create_prompt("greeting", "desc", "v1: {{ name }}", status="active")
    registry.add_version("greeting", "v2: {{ name }}", is_active=True, status="active")

    _text, row = registry.get_prompt("greeting", variables={"name": "Ada"})
    assert row.version == 2
    assert row.is_active is True


def test_get_prompt_renders_specific_version_regardless_of_status(registry):
    # Explicit-version lookups aren't gated by status/is_active — only
    # the no-version "give me whatever's active" path is.
    registry.create_prompt("greeting", "desc", "v1: {{ name }}")   # draft
    registry.add_version("greeting", "v2: {{ name }}", is_active=True, status="active")

    v1_text, v1_row = registry.get_prompt("greeting", version=1, variables={"name": "Ada"})
    v2_text, v2_row = registry.get_prompt("greeting", version=2, variables={"name": "Ada"})
    assert v1_text == "v1: Ada"
    assert v1_row.status == "draft"
    assert v2_text == "v2: Ada"
    assert v2_row.status == "active"


def test_get_prompt_no_variables_needed(registry):
    registry.create_prompt("static", "desc", "no variables here", status="active")
    text, _row = registry.get_prompt("static")
    assert text == "no variables here"


def test_get_prompt_missing_name_raises_value_error(registry):
    with pytest.raises(ValueError):
        registry.get_prompt("nonexistent")


def test_get_prompt_draft_only_has_no_active_version(registry):
    # A prompt that's never been activated has nothing for the
    # no-explicit-version lookup to find — this is the direct
    # consequence of "draft" being the default, not a separate bug.
    registry.create_prompt("greeting", "desc", "hi")
    with pytest.raises(ValueError):
        registry.get_prompt("greeting")


def test_get_prompt_missing_version_raises_value_error(registry):
    registry.create_prompt("greeting", "desc", "hi")
    with pytest.raises(ValueError):
        registry.get_prompt("greeting", version=99)


def test_get_prompt_bad_template_raises_template_error(registry):
    registry.create_prompt("broken", "desc", "{{ unclosed", status="active")
    with pytest.raises(TemplateError):
        registry.get_prompt("broken")


def test_get_prompt_undefined_variable_raises_template_error(registry):
    registry.create_prompt("strict", "desc", "{{ missing.attr.chain }}", status="active")
    # Jinja2's default Undefined silently renders empty for a bare
    # variable, but attribute access on an Undefined raises — exercises
    # the wrap-into-TemplateError path with a realistic failure, not a
    # contrived syntax error.
    with pytest.raises(TemplateError):
        registry.get_prompt("strict", variables={})


def test_get_prompt_blocks_dangerous_attribute_access_in_template_source(registry):
    # Real security regression test for the SandboxedEnvironment switch
    # (backend/ai/prompt_registry.py) — a classic Jinja2 SSTI payload
    # that reaches for object internals via attribute traversal. This is
    # about the TEMPLATE SOURCE itself doing this (an admin-authored
    # prompt, in this app's threat model), not a caller-supplied
    # variable value — variable-value safety is covered separately in
    # test_prompt_builder.py's own security test.
    payload = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
    registry.create_prompt("ssti", "desc", payload, status="active")
    with pytest.raises(TemplateError):
        registry.get_prompt("ssti")


def test_get_prompt_normal_template_unaffected_by_sandboxing(registry):
    # The sandbox must not change output for any legitimate template —
    # plain variable substitution isn't a restricted operation.
    registry.create_prompt("normal", "desc", "Hello, {{ name }}! Cost: 5 & 10 < 20.", status="active")
    text, _row = registry.get_prompt("normal", variables={"name": "Ada"})
    assert text == "Hello, Ada! Cost: 5 & 10 < 20."


# ------------------------------------------------------------ list_prompts
def test_list_prompts_returns_every_version_regardless_of_status(registry):
    registry.create_prompt("a", "desc", "A {{ x }}")                    # draft, v1
    registry.create_prompt("b", "desc", "B {{ x }}", status="active")   # active, v1
    registry.add_version("a", "A v2 {{ x }}")                            # draft, v2

    prompts = registry.list_prompts()
    assert len(prompts) == 3
    seen = sorted((p.name, p.version) for p in prompts)
    assert seen == [("a", 1), ("a", 2), ("b", 1)]


def test_list_prompts_empty_when_none_created(registry):
    assert registry.list_prompts() == []


# ------------------------------------------------------------ get_active_version
def test_get_active_version_returns_none_when_no_prompt(registry):
    assert registry.get_active_version("nonexistent") is None


# ------------------------------------------------------------ get_prompts_by_category
def test_get_prompts_by_category_filters(registry):
    registry.create_prompt("a", "desc", "A", status="active", category="analysis")
    registry.create_prompt("b", "desc", "B", status="active", category="writing")
    registry.add_version("a", "A v2", category="analysis")

    results = registry.get_prompts_by_category("analysis")
    assert {p.name for p in results} == {"a"}
    assert len(results) == 2   # both versions of "a"


def test_get_prompts_by_category_empty_when_no_match(registry):
    registry.create_prompt("a", "desc", "A", category="analysis")
    assert registry.get_prompts_by_category("nonexistent-category") == []


# ------------------------------------------------------------ get_active_prompts
def test_get_active_prompts_filters_by_status_not_is_active(registry):
    registry.create_prompt("a", "desc", "A", status="active")
    registry.create_prompt("b", "desc", "B")   # draft
    # A second active-status version of "a" that isn't the served one —
    # get_active_prompts() should still surface it (status, not is_active).
    registry.add_version("a", "A v2", status="active")

    results = registry.get_active_prompts()
    assert len(results) == 2
    assert all(p.status == "active" for p in results)


def test_get_active_prompts_empty_when_none_active(registry):
    registry.create_prompt("a", "desc", "A")   # draft
    assert registry.get_active_prompts() == []


# ------------------------------------------------------------ get_prompts_by_status
def test_get_prompts_by_status_draft(registry):
    registry.create_prompt("a", "desc", "A")
    registry.create_prompt("b", "desc", "B", status="active")
    results = registry.get_prompts_by_status("draft")
    assert [p.name for p in results] == ["a"]


def test_get_prompts_by_status_archived(registry):
    registry.create_prompt("a", "desc", "A", status="active")
    registry.archive_prompt("a")
    results = registry.get_prompts_by_status("archived")
    assert [p.name for p in results] == ["a"]


# ------------------------------------------------------------ archive_prompt
def test_archive_prompt_sets_status_and_clears_is_active(registry):
    registry.create_prompt("a", "desc", "A", status="active")
    archived = registry.archive_prompt("a")
    assert archived.status == "archived"
    assert archived.is_active is False


def test_archive_prompt_leaves_no_active_version(registry):
    registry.create_prompt("a", "desc", "A", status="active")
    registry.archive_prompt("a")
    assert registry.get_active_version("a") is None


def test_archive_prompt_raises_when_nothing_active(registry):
    registry.create_prompt("a", "desc", "A")   # draft, never activated
    with pytest.raises(ValueError):
        registry.archive_prompt("a")


# ------------------------------------------------------------ activate_prompt
def test_activate_prompt_activates_latest_version(registry):
    registry.create_prompt("a", "desc", "A v1")
    registry.add_version("a", "A v2")
    registry.add_version("a", "A v3")

    activated = registry.activate_prompt("a")
    assert activated.version == 3
    assert activated.status == "active"
    assert activated.is_active is True
    assert registry.get_active_version("a").version == 3


def test_activate_prompt_deactivates_previous_active_version(registry):
    registry.create_prompt("a", "desc", "A v1", status="active")
    registry.add_version("a", "A v2")   # draft

    registry.activate_prompt("a")

    rows = registry.db.query(PromptVersion).filter_by(name="a").all()
    active_rows = [r for r in rows if r.is_active]
    assert len(active_rows) == 1
    assert active_rows[0].version == 2


def test_activate_prompt_raises_for_unknown_name(registry):
    with pytest.raises(ValueError):
        registry.activate_prompt("nonexistent")
