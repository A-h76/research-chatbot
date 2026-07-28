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
"""

import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_MAX_AGE_SECONDS = 15 * 60
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    signup_allowed_fn=None,
    on_user_created=None,
    record_last_login_fn=None,
):
    bp = Blueprint("magic_link", __name__, url_prefix="/auth/magic-link")
    serializer = URLSafeTimedSerializer(secret_key, salt="magic-link")

    def _normalize_email(raw):
        return (raw or "").strip().lower()

    def _rate_limit_key():
        data = request.get_json(silent=True) or {}
        return _normalize_email(data.get("email"))

    def _may_sign_in(email: str) -> bool:
        if signup_allowed_fn is not None:
            ok, _reason = signup_allowed_fn(email)
            return ok
        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            return False
        return True

    @bp.route("", methods=["POST"])
    @limiter.limit("3 per hour", key_func=_rate_limit_key)
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

        token = serializer.dumps({"email": email})
        verify_url = f"{APP_BASE_URL}/auth/magic-link?token={token}"
        html = (
            f"<p>Click below to sign in — this link expires in 15 minutes.</p>"
            f'<p><a href="{verify_url}">Sign in</a></p>'
            f"<p>If you didn't request this, you can ignore this email.</p>"
        )
        email_service.send(
            to=email,
            subject="Your sign-in link",
            html=html,
            text=f"Sign in: {verify_url}",
        )
        return generic_response

    @bp.route("/verify", methods=["POST"])
    @limiter.limit("20 per hour")
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
        if not email:
            return jsonify({"error": "invalid_token"}), 401

        if not _may_sign_in(email):
            log_security_event("magic_link_denied", email=email, stage="verify")
            return jsonify({"error": "not_allowed"}), 403

        db = SessionLocal()
        try:
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            created = False
            if not user:
                user = User(email=email, name=email, auth_provider="magic")
                db.add(user)
                created = True
            user.email_verified = True
            user.email_verified_at = getattr(user, "email_verified_at", None) or datetime.now(
                timezone.utc
            )
            if not getattr(user, "status", None) or user.status == "pending_verification":
                user.status = "active"
            db.commit()
            if created and on_user_created:
                on_user_created(user, email)

            session["user_id"] = user.id
            session["user_email"] = user.email
            session["session_version"] = int(getattr(user, "session_version", 0) or 0)
            access, refresh = create_jwt(user.id)
            session["jwt"] = {"access": access, "refresh": refresh}
            from security.session_ttl import mark_session_login

            mark_session_login(session)
            if record_last_login_fn:
                record_last_login_fn(user.id)

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
