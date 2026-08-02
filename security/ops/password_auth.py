"""Email+password foundations — register, verify, login, reset, email change.

Uses Werkzeug password hashing (pbkdf2/scrypt). Google OAuth and magic link
remain available; these routes enable standard email/password signup.
Emails go through TransactionalEmailService.handle(EmailEvent.*) only.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String, select
from werkzeug.security import check_password_hash, generate_password_hash

from backend.services.email import EmailEvent


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

    class EmailChangeToken(Base):
        __tablename__ = "email_change_tokens"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        new_email = Column(String(320), nullable=False)
        token_hash = Column(String(64), unique=True, nullable=False)
        expires_at = Column(DateTime, nullable=False)
        used_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return EmailVerificationToken, PasswordResetToken, EmailChangeToken


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_ALLOWED_ROLES = frozenset({"student", "researcher", "professor", "industry"})
_ALLOWED_GOALS = frozenset(
    {"publish", "thesis", "lit_review", "discover", "write", "explore"}
)
_ALLOWED_EXPERIENCE = frozenset({"beginner", "intermediate", "advanced"})
_ALLOWED_FIELDS = frozenset(
    {
        "ai",
        "medicine",
        "physics",
        "economics",
        "biology",
        "chemistry",
        "cs",
        "social",
        "engineering",
        "other",
    }
)


class PasswordAuthService:
    VERIFY_TTL_HOURS = 24
    RESET_TTL_MINUTES = 30
    EMAIL_CHANGE_TTL_HOURS = 24

    def __init__(
        self,
        SessionLocal,
        User,
        EmailVerificationToken,
        PasswordResetToken,
        *,
        EmailChangeToken=None,
        email_service=None,
        app_base_url: str = "",
        now_fn=None,
        events=None,
        auth_from: str = "",
        noreply_from: str = "",
        invite_service=None,
    ):
        self.SessionLocal = SessionLocal
        self.User = User
        self.EmailVerificationToken = EmailVerificationToken
        self.PasswordResetToken = PasswordResetToken
        self.EmailChangeToken = EmailChangeToken
        self.email_service = email_service
        self.app_base_url = (app_base_url or "").rstrip("/")
        self._now = now_fn or (lambda: datetime.now(timezone.utc))
        self.events = events
        self.signup_allowed_fn = None
        self.auth_from = auth_from
        self.noreply_from = noreply_from
        self.invite_service = invite_service

    def _emit(self, event: str, **payload) -> None:
        if not self.email_service:
            return
        handle = getattr(self.email_service, "handle", None)
        if handle:
            handle(event, **payload)
            return
        send = getattr(self.email_service, "send", None)
        if send and payload.get("link"):
            send(
                payload.get("to"),
                event,
                f"<a href=\"{payload['link']}\">{payload['link']}</a>",
                text=payload["link"],
            )

    def _track(self, name: str, **fields) -> None:
        if self.events:
            self.events.record(name, **fields)

    def register(self, *, name: str, email: str, password: str) -> tuple[dict | None, str | None]:
        email = (email or "").strip().lower()
        name = (name or "").strip()[:200]
        if not email or "@" not in email or not password or len(password) < 10:
            return None, "invalid_input"
        if len(password) > 200:
            return None, "invalid_input"

        self._track("signup_started", email=email)
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
            user.plan = "free"
            db.add(user)
            db.commit()
            db.refresh(user)
            raw = self._issue_verification(db, user.id)
            link = f"{self.app_base_url}/auth/verify-email?token={raw}"
            self._emit(
                EmailEvent.USER_REGISTERED,
                to=email,
                name=name,
                link=link,
                hours=self.VERIFY_TTL_HOURS,
            )
            self._track("signup_completed", user_id=user.id, email=email)
            if self.invite_service:
                try:
                    self.invite_service.consume_invite_for_email(email)
                except Exception:
                    pass
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
            already = bool(getattr(user, "email_verified", False))
            row.used_at = self._now()
            user.email_verified = True
            user.email_verified_at = self._now()
            user.status = "active"
            db.commit()
            self._track("email_verified", user_id=user.id)
            if not already:
                self._emit(
                    EmailEvent.EMAIL_VERIFIED,
                    to=user.email,
                    name=user.name or "",
                    cta_url=f"{self.app_base_url}/auth/sign-in",
                )
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
                self._track("login_failed", email=email)
                return None, "invalid_credentials"
            if not check_password_hash(user.password_hash, password or ""):
                self._track("login_failed", user_id=user.id, email=email)
                return None, "invalid_credentials"
            status = (getattr(user, "status", None) or "active").lower()
            if status in {"suspended", "deleted"}:
                return None, "account_inactive"
            if status == "pending_verification" or not getattr(user, "email_verified", False):
                return None, "email_unverified"
            self._track("password_login", user_id=user.id, email=email)
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
            if not user:
                return
            raw = secrets.token_urlsafe(32)
            db.add(
                self.PasswordResetToken(
                    user_id=user.id,
                    token_hash=_hash(raw),
                    expires_at=self._now() + timedelta(minutes=self.RESET_TTL_MINUTES),
                )
            )
            db.commit()
            link = f"{self.app_base_url}/auth/reset-password?token={raw}"
            self._emit(
                EmailEvent.PASSWORD_RESET_REQUESTED,
                to=email,
                name=user.name or "",
                link=link,
                minutes=self.RESET_TTL_MINUTES,
            )
            self._track("password_reset_requested", user_id=user.id, email=email)
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
            user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            row.used_at = self._now()
            email = user.email
            name = user.name or ""
            db.commit()
            self._track("password_changed", user_id=user.id)
            self._track("password_reset_completed", user_id=user.id)
            self._track("session_revoked_all", user_id=user.id)
            self._emit(
                EmailEvent.PASSWORD_CHANGED,
                to=email,
                name=name,
                cta_url=f"{self.app_base_url}/auth/sign-in",
            )
            return True, "ok"
        finally:
            db.close()

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> tuple[bool, str, int | None]:
        """Update password for a logged-in user. Returns (ok, reason, session_version)."""
        if not new_password or len(new_password) < 10:
            return False, "invalid_input", None
        if not current_password:
            return False, "current_required", None
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                return False, "not_found", None
            if not getattr(user, "password_hash", None):
                return False, "no_password", None
            if not check_password_hash(user.password_hash, current_password):
                return False, "wrong_password", None
            if check_password_hash(user.password_hash, new_password):
                return False, "same_password", None
            user.password_hash = generate_password_hash(new_password)
            user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            ver = user.session_version
            email = user.email
            name = user.name or ""
            db.commit()
            self._track("password_changed", user_id=user.id)
            self._emit(
                EmailEvent.PASSWORD_CHANGED,
                to=email,
                name=name,
                cta_url=f"{self.app_base_url}/auth/sign-in",
            )
            return True, "ok", ver
        finally:
            db.close()

    def set_password(self, user_id: int, new_password: str) -> tuple[bool, str, int | None]:
        """First-time password for OAuth / magic-link accounts (no existing hash)."""
        if not new_password or len(new_password) < 10:
            return False, "invalid_input", None
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                return False, "not_found", None
            if getattr(user, "password_hash", None):
                return False, "already_has_password", None
            user.password_hash = generate_password_hash(new_password)
            if (getattr(user, "auth_provider", None) or "") in {"google", "magic", "dev", ""}:
                user.auth_provider = "password"
            user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            ver = user.session_version
            email = user.email
            name = user.name or ""
            db.commit()
            self._track("password_set", user_id=user.id)
            self._emit(
                EmailEvent.PASSWORD_CHANGED,
                to=email,
                name=name,
                cta_url=f"{self.app_base_url}/auth/sign-in",
            )
            return True, "ok", ver
        finally:
            db.close()

    def request_email_change(self, user_id: int, new_email: str) -> tuple[bool, str]:
        if not self.EmailChangeToken:
            return False, "not_configured"
        new_email = (new_email or "").strip().lower()
        if not new_email or "@" not in new_email:
            return False, "invalid_email"
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                return False, "not_found"
            if (user.email or "").lower() == new_email:
                return False, "same_email"
            taken = db.execute(
                select(self.User).where(self.User.email == new_email)
            ).scalar_one_or_none()
            if taken:
                return False, "email_taken"
            raw = secrets.token_urlsafe(32)
            db.add(
                self.EmailChangeToken(
                    user_id=user_id,
                    new_email=new_email,
                    token_hash=_hash(raw),
                    expires_at=self._now() + timedelta(hours=self.EMAIL_CHANGE_TTL_HOURS),
                )
            )
            db.commit()
            link = f"{self.app_base_url}/auth/confirm-email-change?token={raw}"
            self._emit(
                EmailEvent.EMAIL_CHANGE_REQUESTED,
                to=new_email,
                name=user.name or "",
                new_email=new_email,
                link=link,
                hours=self.EMAIL_CHANGE_TTL_HOURS,
            )
            return True, "ok"
        finally:
            db.close()

    def confirm_email_change(self, raw_token: str) -> tuple[bool, str]:
        if not self.EmailChangeToken or not raw_token:
            return False, "invalid_token"
        db = self.SessionLocal()
        try:
            row = db.execute(
                select(self.EmailChangeToken).where(
                    self.EmailChangeToken.token_hash == _hash(raw_token),
                    self.EmailChangeToken.used_at.is_(None),
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
            taken = db.execute(
                select(self.User).where(self.User.email == row.new_email)
            ).scalar_one_or_none()
            if taken and taken.id != user.id:
                return False, "email_taken"
            user.email = row.new_email
            user.email_verified = True
            user.email_verified_at = self._now()
            user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            row.used_at = self._now()
            db.commit()
            self._track("email_changed", user_id=user.id)
            return True, "ok"
        finally:
            db.close()

    def complete_onboarding(self, user_id: int, payload: dict | None = None) -> tuple[bool, str]:
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                return False, "not_found"
            data = payload or {}
            skipped = bool(data.get("skipped"))

            role = str(data.get("research_role") or "").strip().lower()
            if role and role not in _ALLOWED_ROLES:
                return False, "invalid_role"
            goal = str(data.get("research_goal") or data.get("goal") or "").strip().lower()
            if goal and goal not in _ALLOWED_GOALS:
                return False, "invalid_goal"
            experience = str(data.get("experience_level") or "").strip().lower()
            if experience and experience not in _ALLOWED_EXPERIENCE:
                return False, "invalid_experience"

            fields_raw = data.get("research_fields") or data.get("fields") or []
            if isinstance(fields_raw, str):
                fields_list = [f.strip().lower() for f in fields_raw.split(",") if f.strip()]
            elif isinstance(fields_raw, list):
                fields_list = [str(f).strip().lower() for f in fields_raw if str(f).strip()]
            else:
                fields_list = []
            fields_list = [f for f in fields_list if f in _ALLOWED_FIELDS][:12]

            if role:
                user.research_role = role
            if fields_list:
                user.research_fields = ",".join(fields_list)
            institution = str(data.get("institution") or "").strip()[:200]
            if institution:
                user.institution = institution
            if goal:
                user.research_goal = goal
            if experience:
                user.experience_level = experience

            focus = str(data.get("research_focus") or "").strip()[:200]
            if focus and not getattr(user, "institution", None):
                user.institution = focus

            user.onboarding_completed_at = self._now()
            db.commit()
            self._track(
                "onboarding_completed",
                user_id=user_id,
                skipped=skipped,
                research_role=getattr(user, "research_role", None),
                research_goal=getattr(user, "research_goal", None),
            )
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
            self._track("session_revoked_all", user_id=user_id)
            return ver
        finally:
            db.close()
