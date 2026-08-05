"""Entitlement service tests (#13)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from quotas.entitlements import EntitlementDenied, EntitlementService
from quotas.models import create_usage_log_model
from quotas.policies import PLAN_LIMITS, WARN_RATIO
from quotas.service import QuotaService


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        plan = Column(String(30), default="free")
        storage_limit_bytes = Column(BigInteger, default=QuotaService.DEFAULT_STORAGE_LIMIT_BYTES)
        monthly_token_used = Column(Integer, default=0)
        monthly_token_limit = Column(Integer, default=100_000)
        monthly_cost_used = Column(Float, default=0.0)
        monthly_cost_limit = Column(Float, default=3.0)
        quota_reset_at = Column(DateTime, nullable=True)

    class StorageUsage(Base):
        __tablename__ = "storage_usage"
        user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
        bytes_used = Column(Integer, default=0)
        file_count = Column(Integer, default=0)

    UsageLog = create_usage_log_model(Base)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    db = SessionLocal()
    db.add(
        User(
            id=1,
            plan="free",
            monthly_token_limit=100,
            quota_reset_at=datetime.now(timezone.utc) + timedelta(days=10),
        )
    )
    db.commit()
    db.close()

    quota = QuotaService(SessionLocal, User, StorageUsage, UsageLog, select)
    ents = EntitlementService(
        SessionLocal=SessionLocal,
        User=User,
        StorageUsage=StorageUsage,
        UsageLog=UsageLog,
        select=select,
        quota_service=quota,
        settings=None,
    )
    return {
        "SessionLocal": SessionLocal,
        "User": User,
        "UsageLog": UsageLog,
        "quota": quota,
        "ents": ents,
    }


def test_plans_include_team_and_enterprise():
    assert "free" in PLAN_LIMITS
    assert "pro" in PLAN_LIMITS
    assert "team" in PLAN_LIMITS
    assert "enterprise" in PLAN_LIMITS


def test_authorize_passes_under_limit(env):
    d = env["ents"].authorize(1, "writing_intelligence", token_estimate=10)
    assert d.ok is True
    assert d.warning is False
    assert d.label == "Writing Intelligence"


def test_authorize_soft_warning_at_80_percent(env):
    db = env["SessionLocal"]()
    u = db.get(env["User"], 1)
    u.monthly_token_used = 85  # of 100
    db.commit()
    db.close()
    d = env["ents"].authorize(1, "chat", token_estimate=5)
    assert d.ok is True
    assert d.warning is True
    assert d.warning_percent >= WARN_RATIO * 100


def test_authorize_hard_block(env, monkeypatch):
    monkeypatch.setenv("DHUND_SUSPEND_AI_QUOTAS", "0")
    db = env["SessionLocal"]()
    u = db.get(env["User"], 1)
    u.monthly_token_used = 95
    db.commit()
    db.close()
    with pytest.raises(EntitlementDenied) as ei:
        env["ents"].authorize(1, "writing_intelligence", token_estimate=20)
    assert ei.value.code == "token_quota_exceeded"
    payload = ei.value.decision.user_payload()
    assert payload["used"] == 95
    assert payload["limit"] == 100
    assert "Writing Intelligence" in payload["message"]
    assert payload["upgrade_hint"] == "Upgrade Plan"


def test_consume_records_ledger(env):
    env["ents"].consume(1, "chat", tokens=7)
    db = env["SessionLocal"]()
    u = db.get(env["User"], 1)
    assert u.monthly_token_used == 7
    logs = db.execute(select(env["UsageLog"])).scalars().all()
    assert logs
    assert getattr(logs[-1], "operation", "") == "chat" or logs[-1].action == "chat"
    db.close()


def test_admin_reset_and_set_limits(env):
    env["ents"].consume(1, "chat", tokens=40)
    snap = env["ents"].admin_reset_usage(1)
    assert snap["token_used"] == 0
    snap2 = env["ents"].admin_set_limits(1, monthly_token_limit=500, plan="pro")
    assert snap2["token_limit"] == 500
    assert snap2["plan"] == "pro"


class _FakeSettings:
    def __init__(self):
        self._v = "0"

    def get(self, key, default=""):
        return self._v if key == "quotas_disabled" else default

    def set(self, key, value, updated_by=None):
        self._v = str(value)

    def record_spend(self, *_a, **_k):
        pass


def test_quotas_disabled_override(env):
    settings = _FakeSettings()
    env["ents"].settings = settings
    db = env["SessionLocal"]()
    u = db.get(env["User"], 1)
    u.monthly_token_used = 100
    db.commit()
    db.close()
    env["ents"].set_quotas_disabled(True)
    d = env["ents"].authorize(1, "chat", token_estimate=50)
    assert d.ok is True
    assert d.code == "quotas_disabled"
