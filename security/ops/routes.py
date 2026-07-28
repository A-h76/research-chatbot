"""Admin ops + password-auth HTTP routes (factory, no import server)."""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, request, session


def create_ops_blueprint(
    *,
    settings_service,
    event_store,
    invite_service,
    password_auth,
    ai_gate,
    quota_service,
    beta_metrics=None,
    email_service=None,
    app_base_url="",
    login_required,
    admin_required,
    mark_session_login=None,
    create_jwt=None,
    record_last_login_fn=None,
    limiter=None,
):
    bp = Blueprint("ops", __name__)

    def _rate(spec):
        def deco(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return deco

    # ── User usage ──────────────────────────────────────────────────────
    @bp.route("/api/usage", methods=["GET"])
    @login_required
    def get_usage():
        uid = session["user_id"]
        summary = quota_service.get_usage_summary(uid)
        snap = settings_service.snapshot()
        summary["ai"] = {
            "disabled_globally": snap["ai_disabled"],
            "daily": snap["daily"],
        }
        # Attach cost rollup from gate user snapshot
        try:
            u = ai_gate._user(uid)
            summary["cost"] = {
                "used_usd": u["monthly_cost_used"],
                "limit_usd": u["monthly_cost_limit"],
                "plan": u["plan"],
            }
        except Exception:
            summary["cost"] = {}
        return jsonify(summary)

    @bp.route("/api/auth/logout-all", methods=["POST"])
    @login_required
    def logout_all():
        ver = password_auth.revoke_all_sessions(session["user_id"])
        session["session_version"] = ver
        session.clear()
        return jsonify({"ok": True})

    # ── Password auth ───────────────────────────────────────────────────
    @bp.route("/auth/register", methods=["POST"])
    @_rate("5 per minute")
    def register():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email") or "")
        # Closed-beta gate — same rule as Google/magic
        if hasattr(password_auth, "signup_allowed_fn") and password_auth.signup_allowed_fn:
            ok, reason = password_auth.signup_allowed_fn(email)
            if not ok:
                event_store.record("invite_denied", email=email, reason=reason)
                return jsonify({"error": "not_invited"}), 403
        payload, err = password_auth.register(
            name=str(data.get("name") or ""),
            email=email,
            password=str(data.get("password") or ""),
        )
        if err == "email_taken":
            return jsonify({"error": "email_taken"}), 409
        if err:
            return jsonify({"error": err, "detail": "Name, email, and password (10+ chars) required."}), 400
        return jsonify({"ok": True, "user": payload, "detail": "Check your email to verify your account."}), 201

    @bp.route("/auth/verify-email", methods=["GET", "POST"])
    @_rate("20 per hour")
    def verify_email():
        token = request.args.get("token") or (request.get_json(silent=True) or {}).get("token") or ""
        ok, reason = password_auth.verify_email(str(token))
        if request.method == "GET":
            if ok:
                return redirect("/login?verified=1")
            return redirect(f"/login?verify_error={reason}")
        if not ok:
            return jsonify({"error": reason}), 400
        return jsonify({"ok": True})

    @bp.route("/auth/password-login", methods=["POST"])
    @_rate("5 per minute")
    def password_login():
        data = request.get_json(silent=True) or {}
        user, err = password_auth.login(
            str(data.get("email") or ""),
            str(data.get("password") or ""),
        )
        if err:
            status = 403 if err in {"email_unverified", "account_inactive"} else 401
            return jsonify({"error": err}), status
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["session_version"] = user.get("session_version", 0)
        if mark_session_login:
            mark_session_login(session)
        if create_jwt:
            access, refresh = create_jwt(user["id"])
            session["jwt"] = {"access": access, "refresh": refresh}
        if record_last_login_fn:
            record_last_login_fn(user["id"])
        return jsonify({"ok": True, "user": {"id": user["id"], "email": user["email"], "name": user["name"]}})

    @bp.route("/auth/forgot-password", methods=["POST"])
    @_rate("5 per hour")
    def forgot_password():
        data = request.get_json(silent=True) or {}
        password_auth.request_password_reset(str(data.get("email") or ""))
        return jsonify({"ok": True, "detail": "If that account exists, a reset email was sent."})

    @bp.route("/auth/reset-password", methods=["POST"])
    @_rate("10 per hour")
    def reset_password():
        data = request.get_json(silent=True) or {}
        ok, reason = password_auth.reset_password(
            str(data.get("token") or ""),
            str(data.get("password") or ""),
        )
        if not ok:
            return jsonify({"error": reason}), 400
        return jsonify({"ok": True})

    # ── Admin ops ───────────────────────────────────────────────────────
    @bp.route("/api/admin/ops/settings", methods=["GET"])
    @login_required
    @admin_required
    def admin_get_settings():
        return jsonify(settings_service.snapshot())

    @bp.route("/api/admin/ops/settings", methods=["PATCH"])
    @login_required
    @admin_required
    def admin_patch_settings():
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        if "ai_disabled" in data:
            settings_service.set_ai_disabled(bool(data["ai_disabled"]), updated_by=uid)
            event_store.record(
                "admin_ai_kill_switch",
                user_id=uid,
                ai_disabled=bool(data["ai_disabled"]),
            )
        if "daily_ai_budget_usd" in data:
            try:
                amount = float(data["daily_ai_budget_usd"])
            except (TypeError, ValueError):
                return jsonify({"error": "invalid_budget"}), 400
            settings_service.set_daily_budget_usd(amount, updated_by=uid)
            event_store.record(
                "admin_budget_changed",
                user_id=uid,
                daily_ai_budget_usd=amount,
            )
        return jsonify(settings_service.snapshot())

    @bp.route("/api/admin/ops/security-events", methods=["GET"])
    @login_required
    @admin_required
    def admin_security_events():
        limit = min(int(request.args.get("limit") or 100), 500)
        event = request.args.get("event") or None
        return jsonify({"items": event_store.list_recent(limit=limit, event=event)})

    @bp.route("/api/admin/ops/invites", methods=["GET"])
    @login_required
    @admin_required
    def admin_list_invites():
        include_used = request.args.get("include_used") in {"1", "true", "yes"}
        return jsonify({"items": invite_service.list_invites(include_used=include_used)})

    @bp.route("/api/admin/ops/invites", methods=["POST"])
    @login_required
    @admin_required
    def admin_create_invite():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email") or "").strip().lower()
        if not email or "@" not in email:
            return jsonify({"error": "email_required"}), 400
        raw = invite_service.create_invite(email, created_by=session["user_id"])
        signup_url = f"{app_base_url.rstrip('/')}/login"
        sent = False
        if email_service and data.get("send_email", True):
            html = (
                f"<p>You've been invited to the Dhund closed beta.</p>"
                f"<p>Sign in with Google or magic link using <b>{email}</b>:</p>"
                f'<p><a href="{signup_url}">{signup_url}</a></p>'
                f"<p>This invite expires in 14 days.</p>"
            )
            sent = bool(
                email_service.send(
                    to=email,
                    subject="You're invited to Dhund (closed beta)",
                    html=html,
                    text=f"Sign in at {signup_url} with {email}",
                )
            )
        return jsonify({"ok": True, "email": email, "token": raw, "email_sent": sent}), 201

    @bp.route("/api/admin/ops/beta-metrics", methods=["GET"])
    @login_required
    @admin_required
    def admin_beta_metrics():
        if beta_metrics is None:
            return jsonify({"error": "not_configured"}), 503
        days = min(max(int(request.args.get("days") or 7), 1), 90)
        return jsonify(beta_metrics.snapshot(days=days))

    @bp.route("/api/admin/ops/health", methods=["GET"])
    @login_required
    @admin_required
    def admin_ops_health():
        snap = settings_service.snapshot()
        return jsonify(
            {
                "ok": True,
                "ai_disabled": snap["ai_disabled"],
                "daily": snap["daily"],
            }
        )

    return bp
