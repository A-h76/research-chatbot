"""Magic-link (passwordless email) auth — a third login method alongside
Google OAuth and DEV_AUTO_LOGIN, not a replacement for either. Same
session shape as both (session["user_id"]/session["user_email"]) so
every existing @login_required route works identically regardless of
which method got the user there.

Built as a factory (create_magic_link_blueprint), not via `import
server`: server.py is normally run directly (`python server.py`), which
Python executes as `__main__` — a module named "server" reaching back
with `import server` would import the *file* a second time under a
different module identity and re-run everything up to that same import,
recursing. Passing the handful of things this module needs explicitly
avoids that entirely, and is a cleaner dependency direction anyway
(Constitution Principle 9) than reaching into another module's globals.

Phase 3: tokens are single-use (jti stored hashed); request rate limits
combine email + IP.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session
from flask_limiter.util import get_remote_address
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import Column, DateTime, Integer, String, select

TOKEN_MAX_AGE_SECONDS = 15 * 60
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_magic_link_token_model(Base):
    """Single-use magic-link jti store (Phase 3 / F2.4)."""

    class MagicLinkToken(Base):
        __tablename__ = "magic_link_tokens"
        id = Column(Integer, primary_key=True)
        token_hash = Column(String(64), unique=True, nullable=False)
        email = Column(String(320), nullable=False)
        expires_at = Column(DateTime, nullable=False)
        used_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return MagicLinkToken


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def create_magic_link_blueprint(
    *,
    secret_key,
    limiter,
    email_service,
    SessionLocal,
    User,
    select,
    ALLOWED_EMAILS,
    APP_BASE_URL,
    create_jwt,
    log_security_event,
    MagicLinkToken,
    signup_allowed_fn=None,
    on_user_created=None,
    record_last_login_fn=None,
):
    bp = Blueprint("magic_link", __name__, url_prefix="/auth/magic-link")
    serializer = URLSafeTimedSerializer(secret_key, salt="magic-link")
    bp._serializer = serializer  # tests mint via issue_token()

    def _normalize_email(raw):
        return (raw or "").strip().lower()

    def _email_rate_key():
        data = request.get_json(silent=True) or {}
        return "ml-email:" + _normalize_email(data.get("email"))

    def _ip_rate_key():
        return "ml-ip:" + (get_remote_address() or "unknown")

    def _may_sign_in(email: str) -> bool:
        if signup_allowed_fn is not None:
            ok, _reason = signup_allowed_fn(email)
            return ok
        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            return False
        return True

    def issue_token(email: str) -> str:
        """Mint a single-use signed token and persist its jti hash."""
        email = _normalize_email(email)
        jti = secrets.token_urlsafe(24)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_MAX_AGE_SECONDS)
        db = SessionLocal()
        try:
            db.add(
                MagicLinkToken(
                    token_hash=_hash_jti(jti),
                    email=email,
                    expires_at=expires_at,
                )
            )
            db.commit()
        finally:
            db.close()
        return serializer.dumps({"email": email, "jti": jti})

    bp.issue_token = issue_token

    @bp.route("", methods=["POST"])
    @limiter.limit("20 per hour", key_func=_ip_rate_key)
    @limiter.limit("3 per hour", key_func=_email_rate_key)
    def request_magic_link():
        data = request.get_json(silent=True) or {}
        email = _normalize_email(data.get("email"))
        if not email or not _EMAIL_RE.match(email):
            return jsonify({"error": "invalid_email"}), 400

        # Deliberately generic response regardless of whether the email is
        # actually allowed — confirming/denying via the response would let
        # an attacker enumerate valid/allowlisted addresses.
        generic_response = jsonify(
            {
                "ok": True,
                "detail": "If that email is allowed to sign in, a login link has been sent.",
            }
        )

        if not _may_sign_in(email):
            log_security_event("magic_link_denied", email=email)
            return generic_response

        token = issue_token(email)
        verify_url = f"{APP_BASE_URL}/auth/magic-link?token={token}"
        handle = getattr(email_service, "handle", None)
        if handle:
            from backend.services.email import EmailEvent

            email_service.handle(
                EmailEvent.MAGIC_LINK_REQUESTED,
                to=email,
                link=verify_url,
            )
        elif getattr(email_service, "send_magic_link", None):
            email_service.send_magic_link(to=email, link=verify_url)
        else:
            email_service.send(
                to=email,
                subject="Your Dhund sign-in link",
                html=f'<p><a href="{verify_url}">Sign in</a></p>',
                text=f"Sign in: {verify_url}",
            )
        return generic_response

    @bp.route("/verify", methods=["POST"])
    @limiter.limit("20 per hour", key_func=_ip_rate_key)
    def verify_magic_link():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify({"error": "token_required"}), 400

        try:
            payload = serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        except SignatureExpired:
            log_security_event("magic_link_verify_failed", reason="expired")
            return jsonify({"error": "token_expired"}), 401
        except BadSignature:
            log_security_event("magic_link_verify_failed", reason="bad_signature")
            return jsonify({"error": "invalid_token"}), 401

        email = payload.get("email")
        jti = payload.get("jti")
        if not email or not jti:
            return jsonify({"error": "invalid_token"}), 401

        if not _may_sign_in(email):
            log_security_event("magic_link_denied", email=email, stage="verify")
            return jsonify({"error": "not_allowed"}), 403

        db = SessionLocal()
        try:
            row = db.execute(
                select(MagicLinkToken).where(
                    MagicLinkToken.token_hash == _hash_jti(jti),
                    MagicLinkToken.used_at.is_(None),
                )
            ).scalar_one_or_none()
            if row is None:
                log_security_event("magic_link_verify_failed", reason="reused_or_unknown", email=email)
                return jsonify({"error": "invalid_token", "detail": "token_already_used"}), 401
            now = datetime.now(timezone.utc)
            exp = row.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                log_security_event("magic_link_verify_failed", reason="expired_row", email=email)
                return jsonify({"error": "token_expired"}), 401
            if (row.email or "").lower() != email:
                return jsonify({"error": "invalid_token"}), 401

            # Consume before creating session — single-use (Phase 3 / F2.4).
            row.used_at = now

            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            created = False
            if not user:
                user = User(email=email, name=email, auth_provider="magic")
                db.add(user)
                created = True
            user.email_verified = True
            user.email_verified_at = getattr(user, "email_verified_at", None) or now
            if not getattr(user, "status", None) or user.status == "pending_verification":
                user.status = "active"
            db.commit()
            if created and on_user_created:
                on_user_created(user, email)

            session["user_id"] = user.id
            session["user_email"] = user.email
            session["session_version"] = int(getattr(user, "session_version", 0) or 0)
            access, refresh = create_jwt(
                user.id, session_version=int(getattr(user, "session_version", 0) or 0)
            )
            session["jwt"] = {"access": access, "refresh": refresh}
            from security.session_ttl import mark_session_login

            mark_session_login(session)
            if record_last_login_fn:
                record_last_login_fn(user.id)
            log_security_event("magic_link_login", email=email, user_id=user.id)

            return jsonify(
                {
                    "ok": True,
                    "user_id": user.id,
                    "access_token": access,
                    "refresh_token": refresh,
                }
            )
        finally:
            db.close()

    return bp
