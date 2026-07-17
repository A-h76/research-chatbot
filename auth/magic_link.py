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

from flask import Blueprint, request, session, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

TOKEN_MAX_AGE_SECONDS = 15 * 60
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_magic_link_blueprint(*, secret_key, limiter, email_service,
                                SessionLocal, User, select, ALLOWED_EMAILS,
                                APP_BASE_URL, create_jwt, log_security_event):
    bp = Blueprint("magic_link", __name__, url_prefix="/auth/magic-link")
    serializer = URLSafeTimedSerializer(secret_key, salt="magic-link")

    def _normalize_email(raw):
        return (raw or "").strip().lower()

    def _rate_limit_key():
        data = request.get_json(silent=True) or {}
        return _normalize_email(data.get("email"))

    @bp.route("", methods=["POST"])
    @limiter.limit("3 per hour", key_func=_rate_limit_key)
    def request_magic_link():
        data = request.get_json(silent=True) or {}
        email = _normalize_email(data.get("email"))
        if not email or not _EMAIL_RE.match(email):
            return jsonify({"error": "invalid_email"}), 400

        # Deliberately generic response regardless of whether the email is
        # actually allowed — confirming/denying via the response would let
        # an attacker enumerate valid/allowlisted addresses. The allowlist
        # check below controls whether an email is sent, not what the
        # caller is told.
        generic_response = jsonify({
            "ok": True,
            "detail": "If that email is allowed to sign in, a login link has been sent.",
        })

        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            log_security_event("magic_link_denied", email=email)
            return generic_response

        token = serializer.dumps({"email": email})
        verify_url = f"{APP_BASE_URL}/auth/magic-link?token={token}"
        html = (
            f"<p>Click below to sign in — this link expires in 15 minutes.</p>"
            f'<p><a href="{verify_url}">Sign in</a></p>'
            f"<p>If you didn't request this, you can ignore this email.</p>"
        )
        email_service.send(to=email, subject="Your sign-in link",
                           html=html, text=f"Sign in: {verify_url}")
        return generic_response

    @bp.route("/verify", methods=["POST"])
    def verify_magic_link():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify({"error": "token_required"}), 400

        try:
            payload = serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        except SignatureExpired:
            return jsonify({"error": "token_expired"}), 401
        except BadSignature:
            return jsonify({"error": "invalid_token"}), 401

        email = payload.get("email")
        if not email:
            return jsonify({"error": "invalid_token"}), 401

        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            # Re-checked here too: the allowlist could change between a
            # link being sent and being clicked, and this is the point
            # that actually grants access, not just sends an email.
            return jsonify({"error": "not_allowed"}), 403

        db = SessionLocal()
        try:
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if not user:
                user = User(email=email, name=email, auth_provider="magic")
                db.add(user)
                db.commit()

            session["user_id"] = user.id
            session["user_email"] = user.email
            access, refresh = create_jwt(user.id)
            session["jwt"] = {"access": access, "refresh": refresh}

            return jsonify({
                "ok": True,
                "user_id": user.id,
                "access_token": access,
                "refresh_token": refresh,
            })
        finally:
            db.close()

    bp._serializer = serializer   # exposed for tests only
    return bp
