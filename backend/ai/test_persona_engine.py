"""Tests for PersonaEngine against a real (in-memory SQLite) DB. Persona
lives on prompt_registry.py's shared private Base (see that module's
docstring for why) — creating that Base's tables here creates personas
too, same as prompt_versions.

Run: pytest backend/ai/test_persona_engine.py -v
"""
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.prompt_registry import Persona, _Base
from backend.ai.persona_engine import PersonaEngine


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def engine(db):
    return PersonaEngine(db, Persona)


# ------------------------------------------------------------ create
def test_create_returns_active_persona(engine):
    p = engine.create("Research Assistant", "desc", "You are a research assistant.")
    assert p.name == "Research Assistant"
    assert p.description == "desc"
    assert p.system_prompt == "You are a research assistant."
    assert p.is_active is True


def test_create_rejects_duplicate_name(engine):
    engine.create("Research Assistant", "desc", "sp")
    with pytest.raises(ValueError):
        engine.create("Research Assistant", "different desc", "different sp")


# ------------------------------------------------------------ get / get_by_name
def test_get_returns_persona_by_id(engine):
    p = engine.create("X", "d", "sp")
    assert engine.get(p.id).name == "X"


def test_get_returns_none_for_missing_id(engine):
    assert engine.get(999999) is None


def test_get_by_name_returns_persona(engine):
    engine.create("X", "d", "sp")
    found = engine.get_by_name("X")
    assert found is not None
    assert found.description == "d"


def test_get_by_name_returns_none_when_missing(engine):
    assert engine.get_by_name("nonexistent") is None


# ------------------------------------------------------------ list_active
def test_list_active_excludes_deactivated(engine):
    a = engine.create("A", "d", "sp")
    engine.create("B", "d", "sp")
    engine.deactivate(a.id)

    active = engine.list_active()
    assert [p.name for p in active] == ["B"]


def test_list_active_includes_multiple_simultaneously(engine):
    # Not the same constraint as PromptVersion.is_active — many personas
    # can be active at once, no partial-unique-per-name index here.
    engine.create("A", "d", "sp")
    engine.create("B", "d", "sp")
    assert {p.name for p in engine.list_active()} == {"A", "B"}


# ------------------------------------------------------------ update
def test_update_changes_given_fields_only(engine):
    p = engine.create("X", "old desc", "old prompt")
    updated = engine.update(p.id, description="new desc")
    assert updated.description == "new desc"
    assert updated.system_prompt == "old prompt"   # untouched field preserved


def test_update_bumps_updated_at(engine):
    # Compares two values read back through the same ORM round-trip
    # rather than constructing one by hand — SQLite doesn't preserve
    # tzinfo, so a hand-built aware datetime compared against a
    # reloaded-naive one would raise, not just be a weaker assertion.
    p = engine.create("X", "d", "sp")
    original_updated_at = p.updated_at
    time.sleep(0.01)

    updated = engine.update(p.id, description="new")
    assert updated.updated_at > original_updated_at


def test_update_raises_for_missing_id(engine):
    with pytest.raises(ValueError):
        engine.update(999999, description="x")


# ------------------------------------------------------------ deactivate
def test_deactivate_sets_is_active_false(engine):
    p = engine.create("X", "d", "sp")
    engine.deactivate(p.id)
    assert engine.get(p.id).is_active is False


def test_deactivate_does_not_delete_the_row(engine):
    p = engine.create("X", "d", "sp")
    engine.deactivate(p.id)
    assert engine.get(p.id) is not None
    assert engine.get_by_name("X") is not None
