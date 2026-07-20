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

from backend.ai.prompt_registry import PromptRegistry, _Base as prompt_base
from backend.ai.seed import seed_prompts, seed_pipelines, seed_all, ModelPreset, DEFAULT_PROMPTS, DEFAULT_PIPELINES


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    prompt_base.metadata.create_all(engine)   # prompt_versions
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ------------------------------------------------------------ seed_prompts
def test_seed_prompts_creates_all_seven(db):
    result = seed_prompts(db)
    assert set(result.keys()) == set(DEFAULT_PROMPTS.keys())
    assert len(result) == 7


def test_seed_prompts_is_renderable(db):
    seed_prompts(db)
    registry = PromptRegistry(db)
    text = registry.get_prompt("paper_summary", variables={"text": "some paper text"})
    assert "some paper text" in text


def test_seed_prompts_idempotent(db):
    seed_prompts(db)
    result_second_run = seed_prompts(db)
    assert len(result_second_run) == 7

    registry = PromptRegistry(db)
    # Still exactly one version each — a second run must not create v2s.
    for name in DEFAULT_PROMPTS:
        versions = db.query(type(registry.get_active_version(name))).filter_by(name=name).all()
        assert len(versions) == 1


def test_seed_prompts_does_not_overwrite_existing_prompt_with_same_name(db):
    # Simulates backfill.py already having seeded "paper_analysis" with
    # different, real content — seed_prompts must not clobber it.
    registry = PromptRegistry(db)
    registry.create_prompt("paper_analysis", "the real one", "REAL EXISTING TEMPLATE {{ text }}")

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
    seed_pipelines(db)   # must not raise "no such table"
    assert db.query(ModelPreset).count() == 3


# ------------------------------------------------------------ seed_all
def test_seed_all_returns_both(db):
    result = seed_all(db)
    assert set(result.keys()) == {"prompts", "pipelines"}
    assert len(result["prompts"]) == 7
    assert len(result["pipelines"]) == 3
