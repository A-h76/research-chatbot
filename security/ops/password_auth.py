"""Email+password foundations — register, verify, login, reset.

Uses Werkzeug password hashing (pbkdf2/scrypt). Magic link + Google remain
primary for closed beta; these routes enable institutional password path.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String, select
from werkzeug.security import check_password_hash, generate_password_hash


def create_email_token_models(Base):
    class EmailVerificationToken(Base):
        __tablename__ = "email_verification_tokens"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        token_hash = Column(String(64), unique=True, nullable=False)
        expires_at = Column(DateTime, nullable=False)
        used_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class PasswordResetToken(Base):
        __tablename__ = "password_reset_tokens"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        token_hash = Column(String(64), unique=True, nullable=False)
        expires_at = Column(DateTime, nullable=False)
        used_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return EmailVerificationToken, PasswordResetToken


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PasswordAuthService:
    VERIFY_TTL_HOURS = 24
    RESET_TTL_HOURS = 2

    def __init__(
        self,
        SessionLocal,
        User,
        EmailVerificationToken,
        PasswordResetToken,
        *,
        email_service=None,
        app_base_url: str = "",
        now_fn=None,
        events=None,
    ):
        self.SessionLocal = SessionLocal
        self.User = User
        self.EmailVerificationToken = EmailVerificationToken
        self.PasswordResetToken = PasswordResetToken
        self.email_service = email_service
        self.app_base_url = (app_base_url or "").rstrip("/")
        self._now = now_fn or (lambda: datetime.now(timezone.utc))
        self.events = events
        self.signup_allowed_fn = None

    def register(self, *, name: str, email: str, password: str) -> tuple[dict | None, str | None]:
        email = (email or "").strip().lower()
        name = (name or "").strip()[:200]
        if not email or not password or len(password) < 10:
            return None, "invalid_input"
        if len(password) > 200:
            return None, "invalid_input"

        db = self.SessionLocal()
        try:
            existing = db.execute(
                select(self.User).where(self.User.email == email)
            ).scalar_one_or_none()
            if existing:
                return None, "email_taken"

            user = self.User(
                email=email,
                name=name or email.split("@")[0],
                auth_provider="password",
            )
            user.password_hash = generate_password_hash(password)
            user.status = "pending_verification"
            user.email_verified = False
            user.plan = "beta"
            db.add(user)
            db.commit()
            db.refresh(user)
            raw = self._issue_verification(db, user.id)
            self._send_verify_email(email, name, raw)
            return {"id": user.id, "email": email, "status": user.status}, None
        finally:
            db.close()

    def _issue_verification(self, db, user_id: int) -> str:
        raw = secrets.token_urlsafe(32)
        db.add(
            self.EmailVerificationToken(
                user_id=user_id,
                token_hash=_hash(raw),
                expires_at=self._now() + timedelta(hours=self.VERIFY_TTL_HOURS),
            )
        )
        db.commit()
        return raw

    def _send_verify_email(self, email: str, name: str, raw: str) -> None:
        if not self.email_service:
            return
        link = f"{self.app_base_url}/auth/verify-email?token={raw}"
        html = (
            f"<p>Hi {name or 'there'},</p>"
            f"<p>Welcome to Dhund.</p>"
            f"<p><a href=\"{link}\">Verify Email</a></p>"
            f"<p>This link expires in {self.VERIFY_TTL_HOURS} hours.</p>"
        )
        self.email_service.send(
            to=email,
            subject="Verify your Dhund account",
            html=html,
            text=f"Verify your Dhund account: {link}",
        )

    def verify_email(self, raw_token: str) -> tuple[bool, str]:
        if not raw_token:
            return False, "invalid_token"
        db = self.SessionLocal()
        try:
            row = db.execute(
                select(self.EmailVerificationToken).where(
                    self.EmailVerificationToken.token_hash == _hash(raw_token),
                    self.EmailVerificationToken.used_at.is_(None),
                )
            ).scalar_one_or_none()
            if not row:
                return False, "invalid_token"
            exp = row.expires_at
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp < self._now():
                return False, "expired"
            user = db.get(self.User, row.user_id)
            if not user:
                return False, "invalid_token"
            row.used_at = self._now()
            user.email_verified = True
            user.email_verified_at = self._now()
            user.status = "active"
            db.commit()
            if self.events:
                self.events.record("email_verified", user_id=user.id)
            return True, "ok"
        finally:
            db.close()

    def login(self, email: str, password: str) -> tuple[dict | None, str | None]:
        email = (email or "").strip().lower()
        db = self.SessionLocal()
        try:
            user = db.execute(
                select(self.User).where(self.User.email == email)
            ).scalar_one_or_none()
            if not user or not getattr(user, "password_hash", None):
                if self.events:
                    self.events.record("login_failed", email=email)
                return None, "invalid_credentials"
            if not check_password_hash(user.password_hash, password or ""):
                if self.events:
                    self.events.record("login_failed", user_id=user.id, email=email)
                return None, "invalid_credentials"
            status = (getattr(user, "status", None) or "active").lower()
            if status in {"suspended", "deleted"}:
                return None, "account_inactive"
            if status == "pending_verification" or not getattr(user, "email_verified", False):
                return None, "email_unverified"
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "session_version": int(getattr(user, "session_version", 0) or 0),
            }, None
        finally:
            db.close()

    def request_password_reset(self, email: str) -> None:
        """Always succeeds outwardly (no email enumeration)."""
        email = (email or "").strip().lower()
        db = self.SessionLocal()
        try:
            user = db.execute(
                select(self.User).where(self.User.email == email)
            ).scalar_one_or_none()
            if not user or not getattr(user, "password_hash", None):
                return
            raw = secrets.token_urlsafe(32)
            db.add(
                self.PasswordResetToken(
                    user_id=user.id,
                    token_hash=_hash(raw),
                    expires_at=self._now() + timedelta(hours=self.RESET_TTL_HOURS),
                )
            )
            db.commit()
            if self.email_service:
                link = f"{self.app_base_url}/auth/reset-password?token={raw}"
                self.email_service.send(
                    to=email,
                    subject="Reset your Dhund password",
                    html=f"<p><a href=\"{link}\">Reset password</a></p>"
                    f"<p>Expires in {self.RESET_TTL_HOURS} hours.</p>",
                    text=f"Reset password: {link}",
                )
        finally:
            db.close()

    def reset_password(self, raw_token: str, new_password: str) -> tuple[bool, str]:
        if not raw_token or not new_password or len(new_password) < 10:
            return False, "invalid_input"
        db = self.SessionLocal()
        try:
            row = db.execute(
                select(self.PasswordResetToken).where(
                    self.PasswordResetToken.token_hash == _hash(raw_token),
                    self.PasswordResetToken.used_at.is_(None),
                )
            ).scalar_one_or_none()
            if not row:
                return False, "invalid_token"
            exp = row.expires_at
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp < self._now():
                return False, "expired"
            user = db.get(self.User, row.user_id)
            if not user:
                return False, "invalid_token"
            user.password_hash = generate_password_hash(new_password)
            # Invalidate other sessions
            user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            row.used_at = self._now()
            db.commit()
            if self.events:
                self.events.record("password_changed", user_id=user.id)
                self.events.record("session_revoked_all", user_id=user.id)
            return True, "ok"
        finally:
            db.close()

    def revoke_all_sessions(self, user_id: int) -> int:
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                return 0
            user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            ver = user.session_version
            db.commit()
            if self.events:
                self.events.record("session_revoked_all", user_id=user_id)
            return ver
        finally:
            db.close()
