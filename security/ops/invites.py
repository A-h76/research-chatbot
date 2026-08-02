"""Invite tokens + optional allowlist helpers (open signup by default)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String, select


def create_invite_token_model(Base):
    class InviteToken(Base):
        __tablename__ = "invite_tokens"
        id = Column(Integer, primary_key=True)
        token_hash = Column(String(64), unique=True, nullable=False)
        email = Column(String(320), nullable=False)
        created_by = Column(Integer, nullable=True)
        expires_at = Column(DateTime, nullable=False)
        used_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return InviteToken


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InviteService:
    def __init__(self, SessionLocal, InviteToken, *, now_fn=None, ttl_days: int = 7):
        self.SessionLocal = SessionLocal
        self.InviteToken = InviteToken
        self._now = now_fn or (lambda: datetime.now(timezone.utc))
        self.ttl_days = ttl_days

    def create_invite(self, email: str, *, created_by: int | None = None) -> str:
        raw = secrets.token_urlsafe(32)
        db = self.SessionLocal()
        try:
            row = self.InviteToken(
                token_hash=hash_token(raw),
                email=(email or "").strip().lower(),
                created_by=created_by,
                expires_at=self._now() + timedelta(days=self.ttl_days),
            )
            db.add(row)
            db.commit()
            return raw
        finally:
            db.close()

    def list_invites(self, *, include_used: bool = False, limit: int = 100) -> list[dict]:
        db = self.SessionLocal()
        try:
            q = select(self.InviteToken).order_by(self.InviteToken.id.desc()).limit(min(limit, 500))
            if not include_used:
                q = q.where(self.InviteToken.used_at.is_(None))
            rows = db.execute(q).scalars().all()
            out = []
            now = self._now()
            for r in rows:
                exp = r.expires_at
                if exp and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                out.append(
                    {
                        "id": r.id,
                        "email": r.email,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                        "used_at": r.used_at.isoformat() if r.used_at else None,
                        "expired": bool(exp and exp < now),
                    }
                )
            return out
        finally:
            db.close()

    def email_is_invited(self, email: str) -> bool:
        email = (email or "").strip().lower()
        if not email:
            return False
        db = self.SessionLocal()
        try:
            now = self._now()
            rows = db.execute(
                select(self.InviteToken).where(
                    self.InviteToken.email == email,
                    self.InviteToken.used_at.is_(None),
                )
            ).scalars().all()
            for r in rows:
                exp = r.expires_at
                if exp and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp and exp >= now:
                    return True
            return False
        finally:
            db.close()

    def consume_invite_for_email(self, email: str, raw_token: str | None = None) -> bool:
        """Mark a matching unused invite as used. Returns True if consumed/valid."""
        email = (email or "").strip().lower()
        db = self.SessionLocal()
        try:
            now = self._now()
            q = select(self.InviteToken).where(
                self.InviteToken.email == email,
                self.InviteToken.used_at.is_(None),
            )
            if raw_token:
                q = q.where(self.InviteToken.token_hash == hash_token(raw_token))
            rows = db.execute(q).scalars().all()
            for r in rows:
                exp = r.expires_at
                if exp and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp and exp < now:
                    continue
                r.used_at = now
                db.commit()
                return True
            return False
        finally:
            db.close()


def signup_allowed(
    email: str,
    *,
    allowed_emails: list[str],
    invite_service: InviteService | None,
    require_invite: bool,
) -> tuple[bool, str]:
    """Signup gate. Open by default; invite-only only when require_invite=True.

    ALLOWED_EMAILS is an optional VIP allowlist (always permitted), not a
    hard deny for everyone else.
    """
    email = (email or "").strip().lower()
    if not email:
        return False, "missing_email"

    if allowed_emails and email in allowed_emails:
        return True, "allowlist"

    if invite_service and invite_service.email_is_invited(email):
        return True, "invite"

    if require_invite:
        return False, "not_invited"

    return True, "open"
