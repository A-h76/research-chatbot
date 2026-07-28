"""Key/value system settings — AI kill switch, daily budget, spend counters."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text


def create_system_settings_model(Base):
    class SystemSetting(Base):
        __tablename__ = "system_settings"
        key = Column(String(80), primary_key=True)
        value = Column(Text, nullable=False, default="")
        updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        updated_by = Column(Integer, nullable=True)

    return SystemSetting


class SystemSettingsService:
    KEY_AI_DISABLED = "ai_disabled"
    KEY_DAILY_BUDGET = "daily_ai_budget_usd"
    KEY_DAILY_SPEND = "daily_ai_spend_usd"
    KEY_DAILY_SPEND_DATE = "daily_ai_spend_date"

    def __init__(self, SessionLocal, SystemSetting, *, now_fn=None):
        self.SessionLocal = SessionLocal
        self.SystemSetting = SystemSetting
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def _get(self, db, key: str, default: str = "") -> str:
        row = db.get(self.SystemSetting, key)
        if row is None:
            return default
        return row.value if row.value is not None else default

    def _set(self, db, key: str, value: str, updated_by: int | None = None) -> None:
        row = db.get(self.SystemSetting, key)
        if row is None:
            row = self.SystemSetting(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
        row.updated_at = self._now()
        row.updated_by = updated_by
        db.commit()

    def get(self, key: str, default: str = "") -> str:
        db = self.SessionLocal()
        try:
            return self._get(db, key, default)
        finally:
            db.close()

    def set(self, key: str, value: str, updated_by: int | None = None) -> None:
        db = self.SessionLocal()
        try:
            self._set(db, key, value, updated_by=updated_by)
        finally:
            db.close()

    def is_ai_disabled(self) -> bool:
        return self.get(self.KEY_AI_DISABLED, "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def set_ai_disabled(self, disabled: bool, updated_by: int | None = None) -> None:
        self.set(self.KEY_AI_DISABLED, "1" if disabled else "0", updated_by=updated_by)

    def daily_budget_usd(self) -> float:
        try:
            return float(self.get(self.KEY_DAILY_BUDGET, "10") or 10)
        except ValueError:
            return 10.0

    def set_daily_budget_usd(self, amount: float, updated_by: int | None = None) -> None:
        self.set(self.KEY_DAILY_BUDGET, str(max(0.0, float(amount))), updated_by=updated_by)

    def _roll_daily_spend(self, db) -> float:
        """Reset spend counter when the UTC date changes."""
        today = self._now().strftime("%Y-%m-%d")
        stored_date = self._get(db, self.KEY_DAILY_SPEND_DATE, "")
        if stored_date != today:
            self._set(db, self.KEY_DAILY_SPEND, "0")
            self._set(db, self.KEY_DAILY_SPEND_DATE, today)
            return 0.0
        try:
            return float(self._get(db, self.KEY_DAILY_SPEND, "0") or 0)
        except ValueError:
            return 0.0

    def daily_spend_usd(self) -> float:
        db = self.SessionLocal()
        try:
            return self._roll_daily_spend(db)
        finally:
            db.close()

    def record_spend(self, cost_usd: float) -> float:
        """Add to today's global spend. Returns new total."""
        if cost_usd <= 0:
            return self.daily_spend_usd()
        db = self.SessionLocal()
        try:
            current = self._roll_daily_spend(db)
            new_total = round(current + float(cost_usd), 6)
            self._set(db, self.KEY_DAILY_SPEND, str(new_total))
            return new_total
        finally:
            db.close()

    def daily_budget_status(self) -> dict[str, Any]:
        spend = self.daily_spend_usd()
        budget = self.daily_budget_usd()
        pct = round(100.0 * spend / budget, 2) if budget > 0 else 0.0
        return {
            "spend_usd": spend,
            "budget_usd": budget,
            "percent": pct,
            "paused": budget > 0 and spend >= budget,
            "warn_80": budget > 0 and pct >= 80,
            "warn_95": budget > 0 and pct >= 95,
        }

    def snapshot(self) -> dict[str, Any]:
        budget = self.daily_budget_status()
        return {
            "ai_disabled": self.is_ai_disabled(),
            "daily": budget,
        }
