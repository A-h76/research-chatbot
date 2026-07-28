"""Unified AI access gate — kill switch, status, quotas, daily budget."""

from __future__ import annotations

from typing import Any


# Plan → monthly token + cost limits (USD). Extends QuotaService free defaults.
PLAN_LIMITS: dict[str, dict[str, Any]] = {
    "free": {
        "monthly_token_limit": 100_000,
        "monthly_cost_limit": 3.0,
        "max_projects": 5,
        "max_research_day": 5,
        "max_active_research": 2,
    },
    "beta": {
        "monthly_token_limit": 1_000_000,
        "monthly_cost_limit": 20.0,
        "max_projects": 50,
        "max_research_day": 50,
        "max_active_research": 2,
    },
    "student": {
        "monthly_token_limit": 10_000_000,
        "monthly_cost_limit": 20.0,
        "max_projects": 100,
        "max_research_day": 50,
        "max_active_research": 2,
    },
    "pro": {
        "monthly_token_limit": 50_000_000,
        "monthly_cost_limit": 100.0,
        "max_projects": 500,
        "max_research_day": 200,
        "max_active_research": 4,
    },
}


class AiAccessDenied(Exception):
    """Raised when AI must not run. ``code`` maps to API error strings."""

    def __init__(self, message: str, code: str, *, http_status: int = 429):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message


class AiAccessGate:
    def __init__(
        self,
        *,
        SessionLocal,
        User,
        settings,
        quota_service,
        events=None,
        select=None,
        allow_admin_bypass_kill_switch: bool = True,
    ):
        self.SessionLocal = SessionLocal
        self.User = User
        self.settings = settings
        self.quota_service = quota_service
        self.events = events
        self.select = select
        self.allow_admin_bypass_kill_switch = allow_admin_bypass_kill_switch

    def plan_limits(self, plan: str | None) -> dict[str, Any]:
        return PLAN_LIMITS.get((plan or "beta").lower(), PLAN_LIMITS["beta"])

    def _user(self, user_id: int):
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                raise AiAccessDenied("User not found.", "not_found", http_status=404)
            # Detach fields we need
            return {
                "id": user.id,
                "status": (getattr(user, "status", None) or "active").lower(),
                "email_verified": self._is_verified(user),
                "is_admin": bool(getattr(user, "is_admin", False)),
                "plan": (getattr(user, "plan", None) or "beta").lower(),
                "monthly_cost_used": float(getattr(user, "monthly_cost_used", 0) or 0),
                "monthly_cost_limit": float(
                    getattr(user, "monthly_cost_limit", None)
                    or self.plan_limits(getattr(user, "plan", None)).get(
                        "monthly_cost_limit", 3.0
                    )
                ),
            }
        finally:
            db.close()

    @staticmethod
    def _is_verified(user) -> bool:
        if bool(getattr(user, "email_verified", False)):
            return True
        # Google / magic / dev prove email ownership at login; password users
        # must complete verification.
        provider = (getattr(user, "auth_provider", None) or "google").lower()
        if provider in {"google", "magic", "dev"}:
            return True
        return False

    def assert_user_can_use_ai(self, user_id: int) -> dict:
        """Status + verification — never allow unverified/suspended AI use."""
        u = self._user(user_id)
        if u["status"] in {"suspended", "deleted"}:
            raise AiAccessDenied(
                "Account is not allowed to use AI.",
                "account_inactive",
                http_status=403,
            )
        if u["status"] == "pending_verification" or not u["email_verified"]:
            raise AiAccessDenied(
                "Verify your email before using AI.",
                "email_unverified",
                http_status=403,
            )
        return u

    def assert_ai_enabled(self, user_id: int | None = None) -> None:
        if not self.settings.is_ai_disabled():
            return
        if user_id is not None and self.allow_admin_bypass_kill_switch:
            u = self._user(user_id)
            if u["is_admin"]:
                return
        if self.events and user_id:
            self.events.record("ai_disabled_blocked", user_id=user_id)
        raise AiAccessDenied(
            "AI is temporarily disabled by the operator. Login, projects, and library remain available.",
            "ai_disabled",
            http_status=503,
        )

    def assert_daily_budget(self, user_id: int | None = None) -> dict:
        status = self.settings.daily_budget_status()
        if status.get("warn_95") and self.events:
            self.events.record(
                "daily_budget_warn",
                user_id=user_id,
                percent=status.get("percent"),
                spend=status.get("spend_usd"),
                budget=status.get("budget_usd"),
            )
        if not status.get("paused"):
            return status
        # Admins may continue when kill-switch bypass is on
        if user_id is not None and self.allow_admin_bypass_kill_switch:
            u = self._user(user_id)
            if u["is_admin"]:
                return status
        if self.events:
            self.events.record(
                "daily_budget_exceeded",
                user_id=user_id,
                spend=status.get("spend_usd"),
                budget=status.get("budget_usd"),
            )
        raise AiAccessDenied(
            "Daily AI budget exceeded. Try again tomorrow or contact support.",
            "daily_budget_exceeded",
            http_status=429,
        )

    def assert_token_and_cost_quota(
        self, user_id: int, *, token_estimate: int = 500, cost_estimate: float = 0.0
    ) -> None:
        u = self.assert_user_can_use_ai(user_id)
        limits = self.plan_limits(u["plan"])

        # Apply plan token ceiling onto user row lazily via QuotaService limits
        try:
            self.quota_service.check_token_quota(user_id, token_estimate)
        except Exception as exc:
            # QuotaExceededError from quotas package
            kind = getattr(exc, "kind", "tokens")
            if self.events:
                self.events.record(
                    "ai_quota_exceeded",
                    user_id=user_id,
                    kind=kind,
                    used=getattr(exc, "used", None),
                    limit=getattr(exc, "limit", None),
                )
            raise AiAccessDenied(
                "AI quota exceeded for this month.",
                "token_quota_exceeded",
                http_status=429,
            ) from exc

        cost_limit = u["monthly_cost_limit"] or float(limits["monthly_cost_limit"])
        projected = u["monthly_cost_used"] + max(0.0, float(cost_estimate))
        if cost_limit > 0 and projected > cost_limit:
            if self.events:
                self.events.record(
                    "ai_quota_exceeded",
                    user_id=user_id,
                    kind="cost",
                    used=u["monthly_cost_used"],
                    limit=cost_limit,
                )
            raise AiAccessDenied(
                "Monthly AI cost limit exceeded.",
                "cost_quota_exceeded",
                http_status=429,
            )

    def preflight(
        self,
        user_id: int,
        *,
        token_estimate: int = 500,
        cost_estimate: float = 0.0,
    ) -> dict:
        """Full pre-AI check. Returns user snapshot on success."""
        self.assert_ai_enabled(user_id)
        u = self.assert_user_can_use_ai(user_id)
        self.assert_daily_budget(user_id)
        self.assert_token_and_cost_quota(
            user_id, token_estimate=token_estimate, cost_estimate=cost_estimate
        )
        return u

    def record_usage(
        self,
        user_id: int,
        *,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        if tokens > 0:
            try:
                self.quota_service.increment_tokens(user_id, tokens)
            except Exception:
                pass
        if cost_usd > 0:
            try:
                self.settings.record_spend(cost_usd)
            except Exception:
                pass
            db = self.SessionLocal()
            try:
                user = db.get(self.User, user_id)
                if user is not None:
                    user.monthly_cost_used = float(
                        getattr(user, "monthly_cost_used", 0) or 0
                    ) + float(cost_usd)
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
