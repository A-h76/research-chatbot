"""Tests for backend/ai/seed.py against a real (in-memory SQLite) DB —
idempotency is the important behavior here (this gets called on every
server startup per the task's own note), so it's tested explicitly, not
just "does it insert once."

Run: pytest backend/ai/test_seed.py -v
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.persona_engine import PersonaEngine
from backend.ai.prompt_registry import Persona, PromptRegistry
from backend.ai.prompt_registry import _Base as prompt_base
from backend.ai.seed import (
    DEFAULT_PERSONAS,
    DEFAULT_PIPELINES,
    DEFAULT_PROMPTS,
    DOMAIN_MODULES,
    ModelPreset,
    seed_all,
    seed_personas,
    seed_pipelines,
    seed_prompts,
    seed_system_prompt,
)
from backend.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    prompt_base.metadata.create_all(engine)  # prompt_versions
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ------------------------------------------------------------ seed_prompts
def test_seed_prompts_creates_all_seven(db):
    result = seed_prompts(db)
    assert set(DEFAULT_PROMPTS.keys()) <= set(result.keys())
    assert all(name in result for name in DEFAULT_PROMPTS)


def test_seed_prompts_also_seeds_domain_modules(db):
    result = seed_prompts(db)
    assert set(result.keys()) == set(DEFAULT_PROMPTS.keys()) | set(DOMAIN_MODULES.keys())
    assert len(result) == len(DEFAULT_PROMPTS) + len(DOMAIN_MODULES)


def test_seed_prompts_domain_modules_use_domain_module_category(db):
    seed_prompts(db)
    registry = PromptRegistry(db)
    for name in DOMAIN_MODULES:
        row = registry.get_active_version(name)
        assert row is not None, f"{name} was not seeded"
        assert row.category == "domain_module"
        assert row.status == "active"
        assert row.is_active is True


def test_seed_prompts_domain_medical_is_extension_only(db):
    """domain_medical is appended (by PromptBuilder.build()) after the base
    paper_analysis task text, which already covers the paper content,
    metadata, and core fields — repeating any of that here would send the
    model two competing JSON shapes in one prompt (see prompt_builder.py's
    docstring, and backend/ai/prompts.py's medical_response_format()
    comment for the real call that proved this happens)."""
    seed_prompts(db)
    registry = PromptRegistry(db)
    row = registry.get_active_version("domain_medical")

    assert "{{ text }}" not in row.template
    assert "**Paper Content:**" not in row.template

    # Spot-check a couple of the medical-specific topics by name.
    assert "PICO" in row.template
    assert "GRADE" in row.template
    assert "Target audience" in row.template


def test_seed_prompts_domain_medical_sections_adapt_to_document_type(db):
    """The whole point of this module's structure: rendering the same
    seeded template with a different document_type should show a
    different document-type-specific section and hide the others —
    proves the {% if/elif %} branches actually work, not just that the
    guidance text exists somewhere in the raw template string."""
    from jinja2.sandbox import SandboxedEnvironment

    seed_prompts(db)
    registry = PromptRegistry(db)
    template = registry.get_active_version("domain_medical").template
    env = SandboxedEnvironment()

    research = env.from_string(template).render(document_type="research")
    assert "This document appears to be a research." in research
    assert "PICO extraction" in research
    assert "Target audience" not in research
    assert "Review coverage" not in research

    clinical_guide = env.from_string(template).render(document_type="clinical_guide")
    assert "Target audience" in clinical_guide
    assert "PICO extraction" not in clinical_guide
    assert "Review coverage" not in clinical_guide

    review = env.from_string(template).render(document_type="review")
    assert "Review coverage" in review
    assert "PICO extraction" not in review
    assert "Target audience" not in review

    # Core fields (always-on) appear regardless of document_type.
    for rendered in (research, clinical_guide, review):
        assert "Clinical bottom line" in rendered

    # An unrecognized/other document_type gets only the core section.
    other = env.from_string(template).render(document_type="case_report")
    assert "Clinical bottom line" in other
    assert "PICO extraction" not in other
    assert "Target audience" not in other
    assert "Review coverage" not in other


def test_seed_prompts_domain_ai_ml_is_a_labeled_placeholder(db):
    seed_prompts(db)
    registry = PromptRegistry(db)
    row = registry.get_active_version("domain_ai_ml")
    assert row is not None
    assert "Placeholder" in row.template


def test_seed_prompts_is_renderable(db):
    seed_prompts(db)
    registry = PromptRegistry(db)
    text, _version = registry.get_prompt("paper_summary", variables={"text": "some paper text"})
    assert "some paper text" in text


def test_seed_prompts_are_immediately_active(db):
    # seed_prompts() must produce servable prompts, not drafts sitting
    # unactivated — PromptRegistry's own default status is "draft" now
    # (migration 0015), so this is exercising seed_prompts()'s own
    # status="active" call, not PromptRegistry's default.
    seed_prompts(db)
    registry = PromptRegistry(db)
    for name in DEFAULT_PROMPTS:
        active = registry.get_active_version(name)
        assert active is not None, f"{name} was seeded but never activated"
        assert active.status == "active"


def test_seed_prompts_idempotent(db):
    seed_prompts(db)
    result_second_run = seed_prompts(db)
    assert len(result_second_run) == len(DEFAULT_PROMPTS) + len(DOMAIN_MODULES)

    registry = PromptRegistry(db)
    # Still exactly one version each — a second run must not create v2s.
    for name in list(DEFAULT_PROMPTS) + list(DOMAIN_MODULES):
        versions = db.query(type(registry.get_active_version(name))).filter_by(name=name).all()
        assert len(versions) == 1


def test_seed_prompts_does_not_overwrite_existing_prompt_with_same_name(db):
    # Simulates backfill.py already having seeded "paper_analysis" with
    # different, real content — seed_prompts must not clobber it.
    # status="active" matches how backfill.py's real raw-SQL seed lands
    # (is_active=true, and status='active' after migration 0015's
    # backfill) — a draft row wouldn't be found by seed_prompts()'s own
    # get_active_version()-based idempotency check, and this test would
    # be exercising the wrong scenario.
    registry = PromptRegistry(db)
    registry.create_prompt("paper_analysis", "the real one", "REAL EXISTING TEMPLATE {{ text }}", status="active")

    seed_prompts(db)

    active = registry.get_active_version("paper_analysis")
    assert active.template == "REAL EXISTING TEMPLATE {{ text }}"


# ------------------------------------------------------------ seed_pipelines
def test_seed_pipelines_creates_all_three(db):
    result = seed_pipelines(db)
    assert set(result.keys()) == set(DEFAULT_PIPELINES.keys())
    assert len(result) == 3


def test_seed_pipelines_config_matches_spec(db):
    seed_pipelines(db)
    row = db.query(ModelPreset).filter_by(name="gpt-4o-analysis").first()
    assert json.loads(row.config) == {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 4000}


def test_seed_pipelines_idempotent(db):
    seed_pipelines(db)
    seed_pipelines(db)
    assert db.query(ModelPreset).count() == 3


def test_seed_pipelines_creates_table_if_missing(db):
    # The fixture only creates prompt_versions — model_presets must be
    # created by seed_pipelines itself (no migration owns this table).
    seed_pipelines(db)  # must not raise "no such table"
    assert db.query(ModelPreset).count() == 3


# ------------------------------------------------------------ seed_system_prompt
def test_seed_system_prompt_creates_active_default(db):
    row = seed_system_prompt(db)
    assert row.name == "system_prompt"
    assert row.status == "active"
    assert row.is_active is True
    assert row.template == DEFAULT_SYSTEM_PROMPT


def test_seed_system_prompt_idempotent(db):
    first = seed_system_prompt(db)
    second = seed_system_prompt(db)
    assert first.id == second.id

    registry = PromptRegistry(db)
    versions = registry.get_prompts_by_status("active")
    assert len(versions) == 1  # a second run must not create v2


# ------------------------------------------------------------ seed_personas
def test_seed_personas_creates_all_eight(db):
    result = seed_personas(db)
    assert set(result.keys()) == set(DEFAULT_PERSONAS.keys())
    assert len(result) == 8


def test_seed_personas_are_active_with_real_content(db):
    seed_personas(db)
    engine = PersonaEngine(db, Persona)
    ra = engine.get_by_name("Research Assistant")
    assert ra.is_active is True
    assert len(ra.system_prompt) > 50
    assert "..." not in ra.system_prompt


def test_seed_personas_idempotent(db):
    seed_personas(db)
    result_second_run = seed_personas(db)
    assert len(result_second_run) == 8
    assert db.query(Persona).count() == 8


# ------------------------------------------------------------ seed_all
def test_seed_all_returns_all_four(db):
    result = seed_all(db)
    assert set(result.keys()) == {"prompts", "pipelines", "system_prompt", "personas"}
    assert len(result["prompts"]) == len(DEFAULT_PROMPTS) + len(DOMAIN_MODULES)
    assert len(result["pipelines"]) == 3
    assert result["system_prompt"].name == "system_prompt"
    assert len(result["personas"]) == 8
