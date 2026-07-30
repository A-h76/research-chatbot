"""Unit tests for closed-beta ops (gate, settings, invites, estimates)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from security.ops.estimates import estimate_chat_tokens, estimate_research_cost_usd
from security.ops.events import SecurityEventStore, create_security_event_model
from security.ops.gate import AiAccessDenied, AiAccessGate, PLAN_LIMITS
from security.ops.invites import InviteService, create_invite_token_model, signup_allowed
from security.ops.settings import SystemSettingsService, create_system_settings_model


class FakeUser:
    def __init__(self, **kw):
        self.id = kw.get("id", 1)
        self.status = kw.get("status", "active")
        self.email_verified = kw.get("email_verified", True)
        self.auth_provider = kw.get("auth_provider", "google")
        self.is_admin = kw.get("is_admin", False)
        self.plan = kw.get("plan", "beta")
        self.monthly_cost_used = kw.get("monthly_cost_used", 0.0)
        self.monthly_cost_limit = kw.get("monthly_cost_limit", 20.0)
        self.monthly_token_used = 0
        self.monthly_token_limit = 1_000_000
        self.quota_reset_at = datetime.now(timezone.utc) + timedelta(days=30)
        self.storage_limit_bytes = 1_000_000_000


class FakeQuota:
    def __init__(self, *, exceed=False):
        self.exceed = exceed
        self.increments = []

    def check_token_quota(self, user_id, estimate):
        if self.exceed:
            from quotas import QuotaExceededError

            raise QuotaExceededError("over", kind="tokens", used=1, limit=1)

    def increment_tokens(self, user_id, tokens):
        self.increments.append((user_id, tokens))

    def get_usage_summary(self, user_id):
        return {"tokens": {"used": 0, "limit": 100}}


def _fresh_db():
    class Base(DeclarativeBase):
        pass

    engine = create_engine("sqlite:///:memory:")
    SystemSetting = create_system_settings_model(Base)
    SecurityEvent = create_security_event_model(Base)
    InviteToken = create_invite_token_model(Base)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session, SystemSetting, SecurityEvent, InviteToken


def test_kill_switch_blocks_non_admin():
    Session, SystemSetting, SecurityEvent, _Invite = _fresh_db()
    settings = SystemSettingsService(Session, SystemSetting)
    settings.set_ai_disabled(True)
    users = {1: FakeUser(id=1, is_admin=False)}

    def SessionLocal():
        class S:
            def get(self, model, uid):
                return users.get(uid)

            def close(self):
                pass

            def commit(self):
                pass

            def rollback(self):
                pass

            def add(self, *a, **k):
                pass

        return S()

    gate = AiAccessGate(
        SessionLocal=SessionLocal,
        User=FakeUser,
        settings=settings,
        quota_service=FakeQuota(),
    )
    with pytest.raises(AiAccessDenied) as ei:
        gate.assert_ai_enabled(1)
    assert ei.value.code == "ai_disabled"


def test_kill_switch_allows_admin():
    Session, SystemSetting, *_ = _fresh_db()
    settings = SystemSettingsService(Session, SystemSetting)
    settings.set_ai_disabled(True)
    users = {1: FakeUser(id=1, is_admin=True)}

    def SessionLocal():
        class S:
            def get(self, model, uid):
                return users.get(uid)

            def close(self):
                pass

        return S()

    gate = AiAccessGate(
        SessionLocal=SessionLocal,
        User=FakeUser,
        settings=settings,
        quota_service=FakeQuota(),
    )
    gate.assert_ai_enabled(1)  # no raise


def test_daily_budget_pause():
    Session, SystemSetting, *_ = _fresh_db()
    settings = SystemSettingsService(Session, SystemSetting)
    settings.set_daily_budget_usd(1.0)
    settings.record_spend(1.5)
    status = settings.daily_budget_status()
    assert status["paused"] is True


def test_signup_allowed_allowlist_and_invite():
    Session, _, _, InviteToken = _fresh_db()
    inv = InviteService(Session, InviteToken)
    raw = inv.create_invite("alice@ox.ac.uk")
    assert signup_allowed(
        "alice@ox.ac.uk",
        allowed_emails=[],
        invite_service=inv,
        require_invite=True,
    )[0]
    assert not signup_allowed(
        "stranger@example.com",
        allowed_emails=["a@b.com"],
        invite_service=inv,
        require_invite=False,
    )[0]
    assert signup_allowed(
        "a@b.com",
        allowed_emails=["a@b.com"],
        invite_service=inv,
        require_invite=False,
    )[0]
    assert inv.consume_invite_for_email("alice@ox.ac.uk", raw)


def test_security_event_persists_critical_only():
    Session, _, SecurityEvent, _ = _fresh_db()
    store = SecurityEventStore(Session, SecurityEvent)
    store.record("oauth_denied", user_id=1, email="x@y.com")
    store.record("noisy_debug", user_id=1)  # not persisted
    items = store.list_recent()
    assert len(items) == 1
    assert items[0]["event"] == "oauth_denied"


def test_estimates():
    class L:
        def estimate_cost(self, model, p, c):
            return 0.08

    est = estimate_research_cost_usd(L(), model="gpt-4o-mini", papers_json_chars=40_000)
    assert est["estimated_cost_usd"] == 0.08
    assert estimate_chat_tokens("hello world") >= 200


def test_plan_limits_have_active_research_cap():
    assert PLAN_LIMITS["beta"]["max_active_research"] == 5
    assert PLAN_LIMITS["pro"]["max_active_research"] >= 5


def test_password_user_needs_verification():
    Session, SystemSetting, *_ = _fresh_db()
    settings = SystemSettingsService(Session, SystemSetting)
    users = {
        1: FakeUser(
            id=1,
            auth_provider="password",
            email_verified=False,
            status="pending_verification",
        )
    }

    def SessionLocal():
        class S:
            def get(self, model, uid):
                return users.get(uid)

            def close(self):
                pass

        return S()

    gate = AiAccessGate(
        SessionLocal=SessionLocal,
        User=FakeUser,
        settings=settings,
        quota_service=FakeQuota(),
    )
    with pytest.raises(AiAccessDenied) as ei:
        gate.assert_user_can_use_ai(1)
    assert ei.value.code == "email_unverified"


def test_beta_metrics_snapshot_and_last_login():
    from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, select
    from sqlalchemy.orm import DeclarativeBase

    from security.ops.beta_metrics import BetaMetricsService, record_last_login

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        last_login_at = Column(DateTime, nullable=True)

    class Project(Base):
        __tablename__ = "projects"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
        meta_status = Column(String(20), default="pending")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class DerivedAnalysis(Base):
        __tablename__ = "derived_analyses"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        kind = Column(String(20))
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class Memory(Base):
        __tablename__ = "memories"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        source = Column(String(20), default="chat")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    now = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)

    db = Session()
    u1 = User(created_at=now - timedelta(days=2))
    u2 = User(created_at=now - timedelta(days=10), last_login_at=now - timedelta(days=1))
    db.add_all([u1, u2])
    db.commit()

    p = Project(user_id=u1.id, created_at=now - timedelta(days=1))
    db.add(p)
    db.commit()

    db.add_all(
        [
            UserFile(user_id=u1.id, project_id=p.id, meta_status="done", created_at=now - timedelta(hours=6)),
            UserFile(user_id=u1.id, project_id=p.id, meta_status="done", created_at=now - timedelta(hours=5)),
            UserFile(user_id=u2.id, project_id=None, meta_status="pending", created_at=now - timedelta(days=3)),
        ]
    )
    db.add(DerivedAnalysis(user_id=u1.id, kind="research", created_at=now - timedelta(hours=2)))
    db.add(Memory(user_id=u1.id, source="research", created_at=now - timedelta(hours=1)))
    db.commit()
    u2_id = u2.id
    db.close()

    metrics = BetaMetricsService(Session, User, Project, UserFile, DerivedAnalysis, Memory, select, now_fn=lambda: now)
    snap = metrics.snapshot(days=7)

    assert snap["period_days"] == 7
    assert snap["counts"]["new_users"] == 1
    assert snap["counts"]["returning_users"] == 1
    assert snap["counts"]["new_projects"] == 1
    assert snap["counts"]["papers_analysed"] == 2
    assert snap["counts"]["research_runs"] == 1
    assert snap["counts"]["memories_promoted"] == 1
    assert snap["funnel_all_time"]["users_with_projects"] == 1
    assert snap["funnel_all_time"]["users_2plus_analysed_papers"] == 1
    assert snap["funnel_all_time"]["users_with_research_run"] == 1

    record_last_login(Session, User, u2_id, now_fn=lambda: now)
    db = Session()
    updated = db.get(User, u2_id)
    assert updated.last_login_at.replace(tzinfo=timezone.utc) == now
    db.close()
