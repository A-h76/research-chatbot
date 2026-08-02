"""FeatureFlagService unit tests (#14)."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

from feature_flags.flags import FLAG_DISCOVER_SEARCH, FLAG_WRITING_INTELLIGENCE
from feature_flags.models import create_feature_flag_model
from feature_flags.service import FeatureDisabled, FeatureFlagService


@pytest.fixture
def svc():
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)

    FeatureFlag = create_feature_flag_model(Base)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return FeatureFlagService(SessionLocal, FeatureFlag, select)


def test_known_flags_default_enabled(svc):
    assert svc.is_enabled(FLAG_DISCOVER_SEARCH, user_id=1) is True
    assert svc.is_enabled(FLAG_WRITING_INTELLIGENCE, user_id=1) is True


def test_unknown_flag_defaults_off(svc):
    assert svc.is_enabled("totally_unknown_flag", user_id=1) is False


def test_global_kill_switch(svc):
    svc.set_flag(FLAG_DISCOVER_SEARCH, enabled=False)
    assert svc.is_enabled(FLAG_DISCOVER_SEARCH, user_id=1) is False
    assert svc.is_enabled(FLAG_DISCOVER_SEARCH, user_id=2) is False


def test_per_user_override(svc):
    svc.set_flag(FLAG_DISCOVER_SEARCH, enabled=False)
    svc.set_flag(FLAG_DISCOVER_SEARCH, enabled=True, user_id=7)
    assert svc.is_enabled(FLAG_DISCOVER_SEARCH, user_id=7) is True
    assert svc.is_enabled(FLAG_DISCOVER_SEARCH, user_id=8) is False


def test_rollout_pct_deterministic(svc):
    svc.set_flag(FLAG_WRITING_INTELLIGENCE, enabled=True, rollout_pct=0)
    assert svc.is_enabled(FLAG_WRITING_INTELLIGENCE, user_id=1) is False

    svc.set_flag(FLAG_WRITING_INTELLIGENCE, enabled=True, rollout_pct=100)
    assert svc.is_enabled(FLAG_WRITING_INTELLIGENCE, user_id=1) is True

    svc.set_flag(FLAG_WRITING_INTELLIGENCE, enabled=True, rollout_pct=50)
    a = svc.is_enabled(FLAG_WRITING_INTELLIGENCE, user_id=42)
    b = svc.is_enabled(FLAG_WRITING_INTELLIGENCE, user_id=42)
    assert a is b
    # Without user_id, partial rollout cannot admit traffic.
    assert svc.is_enabled(FLAG_WRITING_INTELLIGENCE, user_id=None) is False


def test_require_raises(svc):
    svc.set_flag(FLAG_DISCOVER_SEARCH, enabled=False)
    with pytest.raises(FeatureDisabled) as exc:
        svc.require(FLAG_DISCOVER_SEARCH, user_id=1)
    assert exc.value.flag_name == FLAG_DISCOVER_SEARCH


def test_list_includes_defaults_and_db_rows(svc):
    svc.set_flag(FLAG_DISCOVER_SEARCH, enabled=False, rollout_pct=10)
    flags = svc.list_flags()
    names = {f["flag_name"] for f in flags}
    assert FLAG_DISCOVER_SEARCH in names
    assert FLAG_WRITING_INTELLIGENCE in names
    discover = next(f for f in flags if f["flag_name"] == FLAG_DISCOVER_SEARCH and f["user_id"] is None)
    assert discover["source"] == "db"
    assert discover["enabled"] is False
    assert discover["rollout_pct"] == 10


def test_evaluate_known(svc):
    snap = svc.evaluate_known(user_id=1)
    assert snap[FLAG_DISCOVER_SEARCH] is True
    assert snap[FLAG_WRITING_INTELLIGENCE] is True
