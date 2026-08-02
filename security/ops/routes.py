"""Admin ops + password-auth HTTP routes (factory, no import server)."""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, session

from security.request_validation import (
    RequestValidationError,
    parse_json_object,
    reject_unknown_fields,
    require_string,
)


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
    oauth_ready=False,
    closed_beta=False,
    entitlement_service=None,
    feature_flag_service=None,
):
    bp = Blueprint("ops", __name__)

    def _rate(spec):
        def deco(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return deco

    def _auth_ctx(**extra):
        return {
            "oauth_ready": oauth_ready,
            "closed_beta": closed_beta,
            "app_base_url": app_base_url,
            **extra,
        }

    # ── Auth pages (Jinja) ──────────────────────────────────────────────
    @bp.route("/auth/sign-in", methods=["GET"])
    def auth_sign_in_page():
        if "user_id" in session:
            return redirect("/")
        return render_template(
            "auth/sign_in.html",
            **_auth_ctx(
                error=request.args.get("error"),
                verified=request.args.get("verified") == "1",
            ),
        )

    @bp.route("/auth/sign-up", methods=["GET"])
    def auth_sign_up_page():
        if "user_id" in session:
            return redirect("/")
        return render_template("auth/sign_up.html", **_auth_ctx())

    @bp.route("/auth/forgot-password", methods=["GET"])
    def auth_forgot_page():
        if "user_id" in session:
            return redirect("/")
        return render_template("auth/forgot_password.html", **_auth_ctx())

    @bp.route("/auth/reset-password", methods=["GET"])
    def auth_reset_page():
        token = request.args.get("token") or ""
        return render_template(
            "auth/reset_password.html",
            **_auth_ctx(token=token),
        )

    @bp.route("/auth/verify-email", methods=["GET", "POST"])
    @_rate("20 per hour")
    def verify_email():
        token = request.args.get("token") or (request.get_json(silent=True) or {}).get("token") or ""
        # Waiting state (no token) — after signup
        if request.method == "GET" and not token:
            return render_template(
                "auth/verify_email.html",
                **_auth_ctx(email=request.args.get("email") or ""),
            )

        ok, reason = password_auth.verify_email(str(token))
        if request.method == "GET":
            if ok:
                return redirect("/auth/email-confirmed")
            return redirect(f"/auth/verify-email?error={reason}")
        if not ok:
            return jsonify({"error": reason}), 400
        return jsonify({"ok": True})

    @bp.route("/auth/email-confirmed", methods=["GET"])
    def auth_email_confirmed():
        return render_template("auth/email_confirmed.html", **_auth_ctx())

    @bp.route("/auth/account-created", methods=["GET"])
    def auth_account_created():
        return render_template(
            "auth/account_created.html",
            **_auth_ctx(email=request.args.get("email") or ""),
        )

    @bp.route("/auth/password-updated", methods=["GET"])
    def auth_password_updated():
        return render_template("auth/password_updated.html", **_auth_ctx())

    @bp.route("/auth/confirm-email-change", methods=["GET"])
    def auth_confirm_email_change_page():
        token = request.args.get("token") or ""
        ok, reason = password_auth.confirm_email_change(str(token))
        return render_template(
            "auth/email_change_result.html",
            **_auth_ctx(ok=ok, reason=reason),
        )

    # ── User usage ──────────────────────────────────────────────────────
    @bp.route("/api/usage", methods=["GET"])
    @login_required
    def get_usage():
        uid = session["user_id"]
        if entitlement_service is not None:
            summary = entitlement_service.get_usage_for_user(uid)
        else:
            summary = quota_service.get_usage_summary(uid)
        snap = settings_service.snapshot()
        summary["ai"] = {
            "disabled_globally": snap["ai_disabled"],
            "daily": snap["daily"],
        }
        try:
            u = ai_gate._user(uid)
            summary["cost"] = {
                "used_usd": u["monthly_cost_used"],
                "limit_usd": u["monthly_cost_limit"],
                "plan": u["plan"],
            }
        except Exception:
            summary.setdefault("cost", {})
        return jsonify(summary)

    @bp.route("/api/auth/logout-all", methods=["POST"])
    @login_required
    def logout_all():
        ver = password_auth.revoke_all_sessions(session["user_id"])
        session["session_version"] = ver
        session.clear()
        return jsonify({"ok": True})

    # ── Password auth APIs ──────────────────────────────────────────────
    @bp.route("/auth/register", methods=["POST"])
    @_rate("5 per minute")
    def register():
        try:
            data = parse_json_object(request.get_json(silent=True), allow_empty=False)
            reject_unknown_fields(data, {"name", "email", "password", "confirm_password"})
            email = require_string(data, "email", max_len=320)
            name = require_string(data, "name", max_len=200, required=False)
            password = require_string(data, "password", max_len=200, min_len=10, strip=False)
            confirm = data.get("confirm_password")
            if confirm is not None and str(confirm) != password:
                return jsonify({"error": "password_mismatch", "detail": "Passwords do not match."}), 400
        except RequestValidationError as exc:
            return exc.to_response()
        if hasattr(password_auth, "signup_allowed_fn") and password_auth.signup_allowed_fn:
            ok, reason = password_auth.signup_allowed_fn(email)
            if not ok:
                event_store.record("invite_denied", email=email, reason=reason)
                return jsonify({"error": "not_invited"}), 403
        payload, err = password_auth.register(
            name=name,
            email=email,
            password=password,
        )
        if err == "email_taken":
            return jsonify({"error": "email_taken"}), 409
        if err:
            return jsonify({"error": err, "detail": "Name, email, and password (10+ chars) required."}), 400
        return jsonify(
            {
                "ok": True,
                "user": payload,
                "detail": "Check your inbox to verify your email.",
                "redirect": f"/auth/verify-email?email={payload['email']}",
            }
        ), 201

    @bp.route("/auth/password-login", methods=["POST"])
    @_rate("5 per minute")
    def password_login():
        try:
            data = parse_json_object(request.get_json(silent=True), allow_empty=False)
            reject_unknown_fields(data, {"email", "password"})
            email = require_string(data, "email", max_len=320)
            password = require_string(data, "password", max_len=200, strip=False)
        except RequestValidationError as exc:
            return exc.to_response()
        user, err = password_auth.login(email, password)
        if err:
            status = 403 if err in {"email_unverified", "account_inactive"} else 401
            return jsonify({"error": err}), status
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["session_version"] = user.get("session_version", 0)
        if mark_session_login:
            mark_session_login(session)
        if create_jwt:
            access, refresh = create_jwt(
                user["id"], session_version=int(user.get("session_version", 0) or 0)
            )
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
        password = str(data.get("password") or "")
        confirm = data.get("confirm_password")
        if confirm is not None and str(confirm) != password:
            return jsonify({"error": "password_mismatch"}), 400
        ok, reason = password_auth.reset_password(
            str(data.get("token") or ""),
            password,
        )
        if not ok:
            return jsonify({"error": reason}), 400
        return jsonify({"ok": True, "redirect": "/auth/password-updated"})

    @bp.route("/auth/change-email", methods=["POST"])
    @login_required
    @_rate("5 per hour")
    def change_email():
        try:
            data = parse_json_object(request.get_json(silent=True), allow_empty=False)
            reject_unknown_fields(data, {"email", "new_email"})
            if "new_email" in data:
                new_email = require_string(data, "new_email", max_len=320)
            else:
                new_email = require_string(data, "email", max_len=320)
        except RequestValidationError as exc:
            return exc.to_response()
        ok, reason = password_auth.request_email_change(session["user_id"], new_email)
        if not ok:
            code = 409 if reason == "email_taken" else 400
            return jsonify({"error": reason}), code
        return jsonify({"ok": True, "detail": "Check your new inbox to confirm the change."})

    @bp.route("/auth/change-password", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def change_password():
        try:
            data = parse_json_object(request.get_json(silent=True), allow_empty=False)
            reject_unknown_fields(data, {"current_password", "password", "new_password", "confirm_password"})
            new_password = require_string(
                data,
                "new_password" if "new_password" in data else "password",
                max_len=200,
                min_len=10,
                strip=False,
            )
            confirm = data.get("confirm_password")
            if confirm is not None and str(confirm) != new_password:
                return jsonify({"error": "password_mismatch", "detail": "Passwords do not match."}), 400
            current = str(data.get("current_password") or "")
        except RequestValidationError as exc:
            return exc.to_response()

        uid = session["user_id"]
        if current:
            ok, reason, ver = password_auth.change_password(uid, current, new_password)
            if reason == "no_password":
                ok, reason, ver = password_auth.set_password(uid, new_password)
        else:
            ok, reason, ver = password_auth.set_password(uid, new_password)
            if not ok and reason == "already_has_password":
                ok, reason, ver = False, "current_required", None

        if not ok:
            status = 400
            detail = {
                "wrong_password": "Current password is incorrect.",
                "current_required": "Current password is required.",
                "no_password": "No password on this account — omit current_password to set one.",
                "already_has_password": "Account already has a password — provide current_password.",
                "same_password": "New password must be different from the current one.",
                "invalid_input": "Password must be at least 10 characters.",
            }.get(reason, reason)
            return jsonify({"error": reason, "detail": detail}), status
        if ver is not None:
            session["session_version"] = ver
        return jsonify({"ok": True, "detail": "Password updated."})

    @bp.route("/api/onboarding/complete", methods=["POST"])
    @login_required
    def onboarding_complete():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            data = {}
        ok, reason = password_auth.complete_onboarding(session["user_id"], data)
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
        signup_url = f"{app_base_url.rstrip('/')}/auth/sign-up"
        sent = False
        if email_service and data.get("send_email", True):
            handle = getattr(email_service, "handle", None)
            if handle:
                from backend.services.email import EmailEvent

                sent = bool(
                    handle(
                        EmailEvent.INVITED,
                        to=email,
                        signup_url=signup_url,
                        days=7,
                    )
                )
            elif getattr(email_service, "send_invite", None):
                sent = bool(email_service.send_invite(to=email, signup_url=signup_url, days=7))
            else:
                sent = bool(
                    email_service.send(
                        to=email,
                        subject="You've been invited to Dhund",
                        html=f"<p>You've been invited to Dhund.</p><p><a href=\"{signup_url}\">{signup_url}</a></p>",
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
        return jsonify({"ok": True, "ai": settings_service.snapshot()})

    # ── Entitlement / quota admin (#13) ─────────────────────────────────
    @bp.route("/api/admin/ops/quotas/<int:user_id>", methods=["GET"])
    @login_required
    @admin_required
    def admin_get_user_quota(user_id: int):
        if entitlement_service is None:
            return jsonify(quota_service.get_usage_summary(user_id))
        return jsonify(entitlement_service.get_usage_for_user(user_id))

    @bp.route("/api/admin/ops/quotas/<int:user_id>", methods=["PATCH"])
    @login_required
    @admin_required
    def admin_patch_user_quota(user_id: int):
        if entitlement_service is None:
            return jsonify({"error": "entitlements_not_configured"}), 503
        data = request.get_json(silent=True) or {}
        try:
            snap = entitlement_service.admin_set_limits(
                user_id,
                monthly_token_limit=data.get("monthly_token_limit"),
                monthly_cost_limit=data.get("monthly_cost_limit"),
                storage_limit_bytes=data.get("storage_limit_bytes"),
                plan=data.get("plan"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        event_store.record(
            "quota_admin_override",
            user_id=session["user_id"],
            target_user_id=user_id,
            fields=list(data.keys()),
        )
        return jsonify({"ok": True, "usage": snap})

    @bp.route("/api/admin/ops/quotas/<int:user_id>/reset", methods=["POST"])
    @login_required
    @admin_required
    def admin_reset_user_quota(user_id: int):
        if entitlement_service is None:
            return jsonify({"error": "entitlements_not_configured"}), 503
        try:
            snap = entitlement_service.admin_reset_usage(user_id)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        event_store.record(
            "quota_admin_reset",
            user_id=session["user_id"],
            target_user_id=user_id,
        )
        return jsonify({"ok": True, "usage": snap})

    @bp.route("/api/admin/ops/quotas/disabled", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_quotas_disabled():
        if entitlement_service is None:
            return jsonify({"error": "entitlements_not_configured"}), 503
        if request.method == "GET":
            return jsonify({"quotas_disabled": entitlement_service.quotas_disabled()})
        data = request.get_json(silent=True) or {}
        disabled = bool(data.get("disabled"))
        entitlement_service.set_quotas_disabled(
            disabled, updated_by=session.get("user_id")
        )
        event_store.record(
            "quotas_disabled_toggled",
            user_id=session.get("user_id"),
            disabled=disabled,
        )
        return jsonify({"ok": True, "quotas_disabled": disabled})

    @bp.route("/api/admin/ops/quotas/analytics", methods=["GET"])
    @login_required
    @admin_required
    def admin_quota_analytics():
        if entitlement_service is None:
            return jsonify({"error": "entitlements_not_configured"}), 503
        days = min(max(int(request.args.get("days") or 30), 1), 365)
        return jsonify(entitlement_service.analytics(days=days))

    # ── Feature flags (#14) ─────────────────────────────────────────────
    @bp.route("/api/admin/ops/feature-flags", methods=["GET"])
    @login_required
    @admin_required
    def admin_list_feature_flags():
        if feature_flag_service is None:
            return jsonify({"error": "feature_flags_not_configured"}), 503
        return jsonify({"flags": feature_flag_service.list_flags()})

    @bp.route("/api/admin/ops/feature-flags/<flag_name>", methods=["GET"])
    @login_required
    @admin_required
    def admin_get_feature_flag(flag_name: str):
        if feature_flag_service is None:
            return jsonify({"error": "feature_flags_not_configured"}), 503
        user_id = request.args.get("user_id", type=int)
        row = feature_flag_service.get_flag(flag_name, user_id=user_id)
        enabled = feature_flag_service.is_enabled(flag_name, user_id=user_id)
        return jsonify(
            {
                "flag": row,
                "evaluated": {"flag_name": flag_name, "user_id": user_id, "enabled": enabled},
            }
        )

    @bp.route("/api/admin/ops/feature-flags/<flag_name>", methods=["PUT", "PATCH"])
    @login_required
    @admin_required
    def admin_set_feature_flag(flag_name: str):
        if feature_flag_service is None:
            return jsonify({"error": "feature_flags_not_configured"}), 503
        data = request.get_json(silent=True) or {}
        if "enabled" not in data:
            return jsonify({"error": "enabled_required", "message": "Body must include enabled"}), 400
        user_id = data.get("user_id")
        if user_id is not None:
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid_user_id"}), 400
        rollout_pct = data.get("rollout_pct", data.get("rolloutPct"))
        if rollout_pct is not None:
            try:
                rollout_pct = int(rollout_pct)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid_rollout_pct"}), 400
        try:
            row = feature_flag_service.set_flag(
                flag_name,
                enabled=bool(data["enabled"]),
                user_id=user_id,
                rollout_pct=rollout_pct,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        event_store.record(
            "feature_flag_set",
            user_id=session.get("user_id"),
            flag_name=flag_name,
            enabled=bool(data["enabled"]),
            target_user_id=user_id,
            rollout_pct=rollout_pct,
        )
        return jsonify({"ok": True, "flag": row})

    return bp
