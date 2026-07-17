"""Unit tests for QuotaService — genuinely isolated, unlike this
project's other self-checks: a throwaway in-memory SQLite DB with just
the tables the service needs, no dependency on server.py or a real DB.
This is possible specifically because QuotaService takes SessionLocal/
User/StorageUsage/UsageLog via its constructor rather than importing
them — the design proves itself here.

Run: pytest quotas/test_service.py -v
"""

from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from quotas.service import QuotaService, QuotaExceededError
from quotas.models import create_usage_log_model


@pytest.fixture
def env():
    """Fresh in-memory DB + a QuotaService bound to it, with one User
    (id=1) at default limits. Every test gets its own engine — no state
    leaks between tests."""
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        storage_limit_bytes = Column(
            BigInteger, default=QuotaService.DEFAULT_STORAGE_LIMIT_BYTES
        )
        monthly_token_used = Column(Integer, default=0)
        monthly_token_limit = Column(Integer, default=QuotaService.DEFAULT_TOKEN_LIMIT)
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
    db.add(User(id=1))
    db.commit()
    db.close()

    service = QuotaService(SessionLocal, User, StorageUsage, UsageLog, select)
    return {
        "SessionLocal": SessionLocal,
        "User": User,
        "StorageUsage": StorageUsage,
        "UsageLog": UsageLog,
        "service": service,
    }


def _set_storage_used(env, bytes_used):
    db = env["SessionLocal"]()
    db.add(env["StorageUsage"](user_id=1, bytes_used=bytes_used))
    db.commit()
    db.close()


# ------------------------------------------------------------ quota exceeded
def test_check_storage_quota_passes_under_limit(env):
    env["service"].check_storage_quota(
        1, 500_000_000
    )  # no StorageUsage row yet = 0 used


def test_check_storage_quota_raises_when_exceeded(env):
    _set_storage_used(env, 900_000_000)
    with pytest.raises(QuotaExceededError) as exc_info:
        env["service"].check_storage_quota(1, 200_000_000)  # 1.1GB > 1GB default limit
    assert exc_info.value.kind == "storage"
    assert exc_info.value.used == 900_000_000
    assert exc_info.value.limit == QuotaService.DEFAULT_STORAGE_LIMIT_BYTES


def test_check_token_quota_passes_under_limit(env):
    env["service"].check_token_quota(1, 50_000)


def test_check_token_quota_raises_when_exceeded(env):
    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    user.monthly_token_used = 95_000
    # Mid-cycle, not yet due for reset — without this, _ensure_reset
    # correctly treats a never-initialized reset_at as "start a fresh
    # window now" (the right behavior for a brand new user's first
    # action) and would zero monthly_token_used right before the check.
    user.quota_reset_at = datetime.now(timezone.utc) + timedelta(days=15)
    db.commit()
    db.close()

    with pytest.raises(QuotaExceededError) as exc_info:
        env["service"].check_token_quota(1, 10_000)  # 105,000 > 100,000 default limit
    assert exc_info.value.kind == "tokens"
    assert exc_info.value.used == 95_000


def test_check_quota_raises_value_error_for_unknown_user(env):
    with pytest.raises(ValueError):
        env["service"].check_storage_quota(999, 1)


# ------------------------------------------------------------ logging
def test_increment_storage_creates_usage_log(env):
    env["service"].increment_storage(1, 12_345)
    db = env["SessionLocal"]()
    logs = (
        db.execute(select(env["UsageLog"]).where(env["UsageLog"].user_id == 1))
        .scalars()
        .all()
    )
    db.close()
    assert len(logs) == 1
    assert logs[0].action == "upload"
    assert logs[0].amount == 12_345


def test_increment_storage_updates_live_storage_usage_counter(env):
    env["service"].increment_storage(1, 12_345)
    env["service"].increment_storage(1, 1_000)
    db = env["SessionLocal"]()
    usage = db.get(env["StorageUsage"], 1)
    db.close()
    assert usage.bytes_used == 13_345
    assert usage.file_count == 2


def test_increment_storage_accepts_explicit_delta_files(env):
    env["service"].increment_storage(
        1, 500, delta_files=0
    )  # e.g. re-upload, no new file
    db = env["SessionLocal"]()
    usage = db.get(env["StorageUsage"], 1)
    db.close()
    assert usage.bytes_used == 500
    assert usage.file_count == 0


def test_increment_tokens_updates_running_total_and_creates_log(env):
    env["service"].increment_tokens(1, 1_500)
    env["service"].increment_tokens(1, 500)

    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    logs = (
        db.execute(select(env["UsageLog"]).where(env["UsageLog"].user_id == 1))
        .scalars()
        .all()
    )
    db.close()

    assert user.monthly_token_used == 2_000
    assert len(logs) == 2
    assert all(l.action == "ai_query" for l in logs)
    assert [l.amount for l in logs] == [1_500, 500]


# ------------------------------------------------------------ monthly reset
def test_monthly_reset_rolls_over_when_reset_at_has_passed(env):
    # now_fn injection, not datetime patching — QuotaService computes
    # "now" through exactly one seam (self._now) specifically so this
    # doesn't need to reach into the module's internals to mock time.
    fixed_now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    service = QuotaService(
        env["SessionLocal"],
        env["User"],
        env["StorageUsage"],
        env["UsageLog"],
        select,
        now_fn=lambda: fixed_now,
    )

    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    user.monthly_token_used = 90_000
    user.quota_reset_at = datetime(
        2026, 1, 15, tzinfo=timezone.utc
    )  # already in the past
    db.commit()
    db.close()

    service.increment_tokens(1, 1_000)

    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    db.close()
    # Reset to 0 first (past due), THEN this call's 1,000 tokens applied —
    # not 91,000, which is what NOT resetting would have produced.
    assert user.monthly_token_used == 1_000
    # SQLite round-trip strips tzinfo on read (see service.py's own note
    # on this) — compare the naive form on both sides rather than
    # asserting the read-back value is aware, which it never will be.
    expected = (fixed_now + QuotaService.RESET_PERIOD).replace(tzinfo=None)
    assert user.quota_reset_at == expected


def test_monthly_reset_does_not_roll_over_before_due(env):
    fixed_now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    service = QuotaService(
        env["SessionLocal"],
        env["User"],
        env["StorageUsage"],
        env["UsageLog"],
        select,
        now_fn=lambda: fixed_now,
    )

    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    user.monthly_token_used = 500
    user.quota_reset_at = datetime(
        2026, 3, 1, tzinfo=timezone.utc
    )  # still in the future
    db.commit()
    db.close()

    service.increment_tokens(1, 1_000)

    db = env["SessionLocal"]()
    user = db.get(env["User"], 1)
    db.close()
    assert user.monthly_token_used == 1_500  # accumulated, not reset


# ------------------------------------------------------------ summary
def test_get_usage_summary_shape_and_percentages(env):
    _set_storage_used(env, 250_000_000)  # 25% of the 1GB default
    env["service"].increment_tokens(1, 25_000)  # 25% of the 100k default

    summary = env["service"].get_usage_summary(1)

    assert summary["storage"]["used_bytes"] == 250_000_000
    assert summary["storage"]["limit_bytes"] == QuotaService.DEFAULT_STORAGE_LIMIT_BYTES
    assert summary["storage"]["percent"] == 25.0
    assert summary["tokens"]["used"] == 25_000
    assert summary["tokens"]["percent"] == 25.0
    assert summary["tokens"]["reset_at"] is not None
