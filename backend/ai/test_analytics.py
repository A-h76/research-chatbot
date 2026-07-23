"""Tests for PromptAnalytics against a real (in-memory SQLite) DB — three
declarative Bases pointed at the same engine (a stand-in Base for
AIUsageLedger/ModelVersion, backend/ai/model_registry.py's real Base for
CostLedgerEntry, backend/ai/prompt_registry.py's real Base for
PromptVersion/PromptExecution), matching PromptAnalytics's actual
real-world usage: one Session, three different Python class hierarchies,
one physical database.

Run: pytest backend/ai/test_analytics.py -v
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.ai.analytics import PromptAnalytics
from backend.ai.model_registry import CostLedgerEntry
from backend.ai.model_registry import _Base as model_base
from backend.ai.prompt_registry import PromptExecution, PromptVersion
from backend.ai.prompt_registry import _Base as prompt_base


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    LegacyBase = declarative_base()

    class ModelVersion(LegacyBase):
        __tablename__ = "model_versions"
        id = Column(Integer, primary_key=True)
        logical_name = Column(String(50))
        provider_model_id = Column(String(100))

    class AIUsageLedger(LegacyBase):
        __tablename__ = "ai_usage_ledger"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        model_version_id = Column(Integer, nullable=False)
        prompt_version_id = Column(Integer, nullable=True)
        prompt_tokens = Column(Integer, default=0)
        completion_tokens = Column(Integer, default=0)
        cost_usd = Column(Float, default=0.0)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    LegacyBase.metadata.create_all(engine)
    model_base.metadata.create_all(engine)  # CostLedgerEntry
    prompt_base.metadata.create_all(engine)  # PromptVersion, PromptExecution
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()

    analytics = PromptAnalytics(db, AIUsageLedger, ModelVersion)

    return {
        "db": db,
        "analytics": analytics,
        "AIUsageLedger": AIUsageLedger,
        "ModelVersion": ModelVersion,
    }


NOW = datetime(2026, 6, 15, 12, 0, 0)
IN_RANGE = NOW
OUT_OF_RANGE = NOW - timedelta(days=90)
START = NOW - timedelta(days=7)
END = NOW + timedelta(days=1)


def _add_legacy_event(
    env,
    user_id=1,
    provider_model_id="gpt-4o",
    prompt_tokens=100,
    completion_tokens=50,
    cost_usd=0.01,
    created_at=IN_RANGE,
    prompt_version_id=None,
):
    mv = env["ModelVersion"](logical_name="utility_model", provider_model_id=provider_model_id)
    env["db"].add(mv)
    env["db"].flush()
    led = env["AIUsageLedger"](
        user_id=user_id,
        model_version_id=mv.id,
        prompt_version_id=prompt_version_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        created_at=created_at,
    )
    env["db"].add(led)
    env["db"].commit()
    return led


def _add_new_event(
    env,
    user_id=1,
    model="gpt-4o-mini",
    prompt_tokens=20,
    completion_tokens=10,
    cost_usd=0.001,
    created_at=IN_RANGE,
    prompt_version_id=None,
):
    r = CostLedgerEntry(
        user_id=user_id,
        model=model,
        action="chat",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost=cost_usd,
        prompt_version_id=prompt_version_id,
        created_at=created_at,
    )
    env["db"].add(r)
    env["db"].commit()
    return r


def _add_prompt(env, name="paper_analysis"):
    pv = PromptVersion(name=name, version=1, template="t", is_active=True, status="active")
    env["db"].add(pv)
    env["db"].commit()
    return pv


def _add_execution(
    env,
    prompt_version_id,
    project_id=None,
    user_id=1,
    tokens_used=30,
    latency_ms=500,
    created_at=IN_RANGE,
    status="success",
):
    ex = PromptExecution(
        prompt_version_id=prompt_version_id,
        project_id=project_id,
        user_id=user_id,
        assembled_prompt="x",
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        status=status,
        created_at=created_at,
    )
    env["db"].add(ex)
    env["db"].commit()
    return ex


# ------------------------------------------------------------ get_usage_by_model
def test_by_model_unifies_legacy_and_new_ledgers(env):
    _add_legacy_event(env, provider_model_id="gpt-4o", cost_usd=0.05)
    _add_new_event(env, model="gpt-4o-mini", cost_usd=0.002)

    rows = {r["model"]: r for r in env["analytics"].get_usage_by_model(START, END)}
    assert set(rows.keys()) == {"gpt-4o", "gpt-4o-mini"}
    assert rows["gpt-4o"]["calls"] == 1
    assert rows["gpt-4o"]["cost_usd"] == pytest.approx(0.05)


def test_by_model_merges_same_model_from_both_ledgers(env):
    _add_legacy_event(env, provider_model_id="gpt-4o", prompt_tokens=100, completion_tokens=50, cost_usd=0.05)
    _add_new_event(env, model="gpt-4o", prompt_tokens=10, completion_tokens=5, cost_usd=0.005)

    rows = {r["model"]: r for r in env["analytics"].get_usage_by_model(START, END)}
    assert rows["gpt-4o"]["calls"] == 2
    assert rows["gpt-4o"]["prompt_tokens"] == 110
    assert rows["gpt-4o"]["cost_usd"] == pytest.approx(0.055)


def test_by_model_excludes_events_outside_date_range(env):
    _add_legacy_event(env, provider_model_id="gpt-4o", created_at=OUT_OF_RANGE)
    rows = env["analytics"].get_usage_by_model(START, END)
    assert rows == []


# ------------------------------------------------------------ get_usage_by_user
def test_by_user_separates_buckets(env):
    _add_legacy_event(env, user_id=1, cost_usd=0.01)
    _add_new_event(env, user_id=2, cost_usd=0.02)

    rows = {r["user_id"]: r for r in env["analytics"].get_usage_by_user(START, END)}
    assert set(rows.keys()) == {1, 2}
    assert rows[1]["cost_usd"] == pytest.approx(0.01)
    assert rows[2]["cost_usd"] == pytest.approx(0.02)


def test_by_user_handles_null_user_id_without_crashing(env):
    _add_new_event(env, user_id=None, cost_usd=0.01)
    rows = env["analytics"].get_usage_by_user(START, END)
    assert any(r["user_id"] is None for r in rows)


# ------------------------------------------------------------ get_usage_by_prompt
def test_by_prompt_combines_cost_from_ledgers_and_latency_from_executions(env):
    pv = _add_prompt(env, name="paper_analysis")
    _add_new_event(env, prompt_version_id=pv.id, cost_usd=0.03, prompt_tokens=100, completion_tokens=50)
    _add_execution(env, prompt_version_id=pv.id, latency_ms=800)
    _add_execution(env, prompt_version_id=pv.id, latency_ms=400)

    rows = {r["prompt_name"]: r for r in env["analytics"].get_usage_by_prompt(START, END)}
    row = rows["paper_analysis"]
    assert row["calls"] == 1  # one cost-ledger event
    assert row["cost_usd"] == pytest.approx(0.03)
    assert row["latency_ms_avg"] == 600.0  # avg(800, 400) from the two executions


def test_by_prompt_unattributed_legacy_rows_bucket_as_unknown(env):
    # AIUsageLedger.prompt_version_id is always None in real deployments
    # today (prompt-engine-audit.md §3's dead-column finding) — this
    # confirms those calls still show up in the total, not silently
    # dropped just because they can't be named.
    _add_legacy_event(env, prompt_version_id=None, cost_usd=0.01)

    rows = {r["prompt_name"]: r for r in env["analytics"].get_usage_by_prompt(START, END)}
    assert "unknown" in rows
    assert rows["unknown"]["cost_usd"] == pytest.approx(0.01)


def test_by_prompt_no_executions_leaves_latency_none(env):
    pv = _add_prompt(env, name="paper_analysis")
    _add_new_event(env, prompt_version_id=pv.id, cost_usd=0.01)

    rows = {r["prompt_name"]: r for r in env["analytics"].get_usage_by_prompt(START, END)}
    assert rows["paper_analysis"]["latency_ms_avg"] is None


# ------------------------------------------------------------ get_usage_by_project
def test_by_project_uses_prompt_execution_only(env):
    pv = _add_prompt(env)
    _add_execution(env, prompt_version_id=pv.id, project_id=7, tokens_used=40, latency_ms=200)
    _add_execution(env, prompt_version_id=pv.id, project_id=7, tokens_used=60, latency_ms=400)
    _add_execution(env, prompt_version_id=pv.id, project_id=None, tokens_used=10, latency_ms=100)

    rows = {r["project_id"]: r for r in env["analytics"].get_usage_by_project(START, END)}
    assert rows[7]["calls"] == 2
    assert rows[7]["tokens_used"] == 100
    assert rows[7]["latency_ms_avg"] == 300.0
    assert rows[None]["calls"] == 1


def test_by_project_has_no_cost_field(env):
    pv = _add_prompt(env)
    _add_execution(env, prompt_version_id=pv.id, project_id=1)
    rows = env["analytics"].get_usage_by_project(START, END)
    assert "cost_usd" not in rows[0]
