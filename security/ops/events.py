"""Durable security_events for high-value actions (not every request)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, select


# Events worth persisting (everything else stays in the security logger only).
PERSIST_EVENTS = frozenset(
    {
        "oauth_denied",
        "magic_link_denied",
        "magic_link_verify_failed",
        "login_failed",
        "password_changed",
        "email_verified",
        "quota_exceeded",
        "ai_quota_exceeded",
        "ai_disabled_blocked",
        "daily_budget_exceeded",
        "daily_budget_warn",
        "virus_detected",
        "authz_denied",
        "invite_denied",
        "invite_accepted",
        "admin_plan_changed",
        "admin_ai_kill_switch",
        "admin_budget_changed",
        "session_revoked_all",
        "research_queue_full",
        "csrf_blocked",
        "jwt_refresh_revoked",
        "dev_login",
        "rate_limit_exceeded",
    }
)


def create_security_event_model(Base):
    class SecurityEvent(Base):
        __tablename__ = "security_events"
        id = Column(Integer, primary_key=True, autoincrement=True)
        event = Column(String(80), nullable=False)
        user_id = Column(Integer, nullable=True)
        detail = Column(Text, nullable=False, default="{}")
        ip = Column(String(64), default="")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return SecurityEvent


class SecurityEventStore:
    def __init__(self, SessionLocal, SecurityEvent, *, log_fn=None):
        self.SessionLocal = SessionLocal
        self.SecurityEvent = SecurityEvent
        # Optional structured logger (server.log_security_event)
        self._log_fn = log_fn

    def record(
        self,
        event: str,
        *,
        user_id: int | None = None,
        ip: str = "",
        **fields: Any,
    ) -> None:
        if self._log_fn is not None:
            try:
                self._log_fn(event, user_id=user_id or "", ip=ip or "", **fields)
            except Exception:
                pass

        if event not in PERSIST_EVENTS:
            return

        # Never persist secrets / research bodies
        safe = {
            k: v
            for k, v in fields.items()
            if k
            not in {
                "password",
                "token",
                "prompt",
                "content",
                "body",
                "authorization",
                "api_key",
            }
        }
        db = self.SessionLocal()
        try:
            db.add(
                self.SecurityEvent(
                    event=event,
                    user_id=user_id,
                    detail=json.dumps(safe, ensure_ascii=False, default=str)[:4000],
                    ip=(ip or "")[:64],
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def list_recent(self, *, limit: int = 100, event: str | None = None) -> list[dict]:
        db = self.SessionLocal()
        try:
            q = select(self.SecurityEvent).order_by(self.SecurityEvent.id.desc()).limit(
                min(limit, 500)
            )
            if event:
                q = q.where(self.SecurityEvent.event == event)
            rows = db.execute(q).scalars().all()
            out = []
            for r in rows:
                try:
                    detail = json.loads(r.detail or "{}")
                except Exception:
                    detail = {}
                out.append(
                    {
                        "id": r.id,
                        "event": r.event,
                        "user_id": r.user_id,
                        "detail": detail,
                        "ip": r.ip or "",
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                )
            return out
        finally:
            db.close()
