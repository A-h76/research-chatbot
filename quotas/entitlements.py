"""Entitlement service — single authorize → consume → record flow.

Routes must not sprinkle quota checks. Call::

    decision = entitlements.authorize(user_id, \"writing_intelligence\")
    # … do work …
    entitlements.consume(user_id, \"writing_intelligence\", tokens=n, cost_usd=c)

Soft limit (≥80%) returns ``warning`` on the decision without blocking.
Hard limit raises ``EntitlementDenied`` with a user-facing payload.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from quotas.operations import get_operation
from quotas.policies import WARN_RATIO, plan_limits
from quotas.service import QuotaExceededError


@dataclass
class EntitlementDecision:
    ok: bool
    operation: str
    label: str
    used: int
    limit: int
    remaining: int
    reset_at: str | None
    plan: str
    warning: bool = False
    warning_percent: float = 0.0
    message: str = ""
    code: str = "ok"
    project_id: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def user_payload(self) -> dict[str, Any]:
        """Shape for 429 / warning UX (never a generic 'quota exceeded')."""
        return {
            "error": self.code if not self.ok else None,
            "operation": self.operation,
            "label": self.label,
            "message": self.message,
            "used": self.used,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_at": self.reset_at,
            "plan": self.plan,
            "warning": self.warning,
            "percent": round(100.0 * self.used / self.limit, 1) if self.limit else 0.0,
            "upgrade_hint": "Upgrade Plan" if not self.ok else None,
            "learn_more": "/settings/account",
        }


class EntitlementDenied(Exception):
    def __init__(self, decision: EntitlementDecision, *, http_status: int = 429):
        super().__init__(decision.message)
        self.decision = decision
        self.http_status = http_status
        self.code = decision.code
        self.message = decision.message


class EntitlementService:
    """Governs all metered operations via QuotaService + plan policy."""

    KEY_QUOTAS_DISABLED = "quotas_disabled"

    def __init__(
        self,
        *,
        SessionLocal,
        User,
        StorageUsage,
        UsageLog,
        select,
        quota_service,
        settings=None,
        events=None,
        now_fn=None,
    ):
        self.SessionLocal = SessionLocal
        self.User = User
        self.StorageUsage = StorageUsage
        self.UsageLog = UsageLog
        self.select = select
        self.quota_service = quota_service
        self.settings = settings
        self.events = events
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def quotas_disabled(self) -> bool:
        if self.settings is None:
            return False
        raw = ""
        try:
            raw = self.settings.get(self.KEY_QUOTAS_DISABLED, "0")
        except Exception:
            return False
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def set_quotas_disabled(self, disabled: bool, *, updated_by: int | None = None) -> None:
        if self.settings is None:
            raise RuntimeError("settings_not_configured")
        self.settings.set(
            self.KEY_QUOTAS_DISABLED,
            "1" if disabled else "0",
            updated_by=updated_by,
        )

    def _snapshot(self, user_id: int) -> dict[str, Any]:
        summary = self.quota_service.get_usage_summary(user_id)
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                raise ValueError(f"no such user: {user_id}")
            plan = (getattr(user, "plan", None) or "beta").lower()
            limits = plan_limits(plan)
            # Prefer explicit user overrides; else plan defaults
            token_limit = int(
                user.monthly_token_limit
                or limits.get("monthly_token_limit")
                or 100_000
            )
            token_used = int(user.monthly_token_used or 0)
            reset_at = user.quota_reset_at
            if reset_at and getattr(reset_at, "tzinfo", None) is None:
                reset_at = reset_at.replace(tzinfo=timezone.utc)
            return {
                "plan": plan,
                "token_used": token_used,
                "token_limit": token_limit,
                "remaining": max(0, token_limit - token_used),
                "reset_at": reset_at.isoformat() if reset_at else summary.get("tokens", {}).get("reset_at"),
                "cost_used": float(getattr(user, "monthly_cost_used", 0) or 0),
                "cost_limit": float(
                    getattr(user, "monthly_cost_limit", None)
                    or limits.get("monthly_cost_limit")
                    or 0
                ),
                "storage": summary.get("storage") or {},
            }
        finally:
            db.close()

    def _decision(
        self,
        *,
        operation: str,
        snap: dict[str, Any],
        ok: bool,
        code: str,
        message: str,
        warning: bool = False,
        project_id: int | None = None,
    ) -> EntitlementDecision:
        op = get_operation(operation)
        used = snap["token_used"]
        limit = snap["token_limit"]
        percent = (used / limit) if limit else 0.0
        return EntitlementDecision(
            ok=ok,
            operation=operation,
            label=op["label"],
            used=used,
            limit=limit,
            remaining=snap["remaining"],
            reset_at=snap["reset_at"],
            plan=snap["plan"],
            warning=warning or (ok and percent >= WARN_RATIO),
            warning_percent=round(100.0 * percent, 1),
            message=message,
            code=code,
            project_id=project_id,
        )

    def authorize(
        self,
        user_id: int,
        operation: str,
        *,
        token_estimate: int | None = None,
        cost_estimate: float | None = None,
        project_id: int | None = None,
        bytes_estimate: int = 0,
    ) -> EntitlementDecision:
        op = get_operation(operation)
        tokens = int(
            token_estimate if token_estimate is not None else op.get("default_tokens") or 0
        )
        cost = float(
            cost_estimate if cost_estimate is not None else op.get("default_cost_usd") or 0.0
        )

        if self.quotas_disabled():
            snap = self._snapshot(user_id)
            return self._decision(
                operation=operation,
                snap=snap,
                ok=True,
                code="quotas_disabled",
                message="Quotas temporarily disabled by an operator.",
                project_id=project_id,
            )

        snap = self._snapshot(user_id)

        # Storage-class ops
        if op.get("category") == "storage" and bytes_estimate > 0:
            try:
                self.quota_service.check_storage_quota(user_id, bytes_estimate)
            except QuotaExceededError as exc:
                st = snap["storage"]
                decision = EntitlementDecision(
                    ok=False,
                    operation=operation,
                    label=op["label"],
                    used=int(exc.used),
                    limit=int(exc.limit),
                    remaining=max(0, int(exc.limit) - int(exc.used)),
                    reset_at=None,
                    plan=snap["plan"],
                    message=(
                        f"{op['label']}: you've reached your storage limit.\n\n"
                        f"Used: {exc.used:,} / {exc.limit:,} bytes"
                    ),
                    code="storage_quota_exceeded",
                    project_id=project_id,
                    extras={"kind": "storage"},
                )
                if self.events:
                    self.events.record(
                        "quota_exceeded",
                        user_id=user_id,
                        operation=operation,
                        kind="storage",
                        used=exc.used,
                        limit=exc.limit,
                    )
                raise EntitlementDenied(decision) from exc

        # Token / cost ops
        if tokens > 0 or op.get("category") == "ai":
            try:
                self.quota_service.check_token_quota(user_id, max(tokens, 1) if tokens else 1)
            except QuotaExceededError as exc:
                days = self._days_until_reset(snap.get("reset_at"))
                reset_msg = f"\n\nResets: {days} day{'s' if days != 1 else ''}" if days is not None else ""
                decision = self._decision(
                    operation=operation,
                    snap={
                        **snap,
                        "token_used": int(exc.used),
                        "token_limit": int(exc.limit),
                        "remaining": 0,
                    },
                    ok=False,
                    code="token_quota_exceeded",
                    message=(
                        f"{op['label']}\n\nYou've reached your monthly limit.\n\n"
                        f"Used: {exc.used:,} / {exc.limit:,}{reset_msg}\n\n"
                        f"Upgrade Plan · Learn More"
                    ),
                    project_id=project_id,
                )
                if self.events:
                    self.events.record(
                        "ai_quota_exceeded",
                        user_id=user_id,
                        operation=operation,
                        kind="tokens",
                        used=exc.used,
                        limit=exc.limit,
                    )
                raise EntitlementDenied(decision) from exc

            cost_limit = float(snap["cost_limit"] or 0)
            if cost_limit > 0 and (snap["cost_used"] + max(0.0, cost)) > cost_limit:
                decision = self._decision(
                    operation=operation,
                    snap=snap,
                    ok=False,
                    code="cost_quota_exceeded",
                    message=(
                        f"{op['label']}\n\nYou've reached your monthly AI cost limit "
                        f"(${snap['cost_used']:.2f} / ${cost_limit:.2f})."
                    ),
                    project_id=project_id,
                )
                if self.events:
                    self.events.record(
                        "ai_quota_exceeded",
                        user_id=user_id,
                        operation=operation,
                        kind="cost",
                    )
                raise EntitlementDenied(decision)

        # Refresh after checks (reset may have run)
        snap = self._snapshot(user_id)
        percent = (snap["token_used"] / snap["token_limit"]) if snap["token_limit"] else 0.0
        warning = percent >= WARN_RATIO
        msg = ""
        if warning:
            msg = (
                f"{op['label']}: you've used {round(100 * percent)}% of your monthly "
                f"allowance ({snap['token_used']:,} / {snap['token_limit']:,})."
            )
        return self._decision(
            operation=operation,
            snap=snap,
            ok=True,
            code="ok",
            message=msg,
            warning=warning,
            project_id=project_id,
        )

    @staticmethod
    def _days_until_reset(reset_at: str | None) -> int | None:
        if not reset_at:
            return None
        try:
            dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = dt - datetime.now(timezone.utc)
            return max(0, int(delta.total_seconds() // 86400))
        except Exception:
            return None

    def consume(
        self,
        user_id: int,
        operation: str,
        *,
        tokens: int = 0,
        cost_usd: float = 0.0,
        bytes_added: int = 0,
        project_id: int | None = None,
    ) -> None:
        op = get_operation(operation)
        if bytes_added:
            self.quota_service.increment_storage(user_id, bytes_added)
        if tokens > 0:
            self.quota_service.increment_tokens(user_id, tokens, skip_log=True)
            self._log_event(
                user_id,
                operation=operation,
                action=op.get("unit") or "tokens",
                amount=tokens,
                project_id=project_id,
            )
        if cost_usd > 0:
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
            if self.settings is not None:
                try:
                    self.settings.record_spend(cost_usd)
                except Exception:
                    pass

    def _log_event(
        self,
        user_id: int,
        *,
        operation: str,
        action: str,
        amount: int,
        project_id: int | None = None,
    ) -> None:
        db = self.SessionLocal()
        try:
            snap = None
            try:
                snap = self._snapshot(user_id)
            except Exception:
                snap = None
            detail = {}
            if snap:
                detail = {
                    "operation": operation,
                    "remaining": snap.get("remaining"),
                    "limit": snap.get("token_limit"),
                    "plan": snap.get("plan"),
                }
            kwargs: dict[str, Any] = {
                "user_id": user_id,
                "action": (operation or action)[:30],
                "amount": int(amount),
            }
            # Optional enriched columns (migration 0039)
            if hasattr(self.UsageLog, "operation"):
                kwargs["operation"] = (operation or "")[:60]
            if hasattr(self.UsageLog, "project_id") and project_id is not None:
                kwargs["project_id"] = int(project_id)
            if hasattr(self.UsageLog, "detail_json"):
                kwargs["detail_json"] = json.dumps(detail)
            db.add(self.UsageLog(**kwargs))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    # ── Admin controls ────────────────────────────────────────────────
    def admin_set_limits(
        self,
        user_id: int,
        *,
        monthly_token_limit: int | None = None,
        monthly_cost_limit: float | None = None,
        storage_limit_bytes: int | None = None,
        plan: str | None = None,
    ) -> dict[str, Any]:
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                raise ValueError("user_not_found")
            if monthly_token_limit is not None:
                user.monthly_token_limit = int(monthly_token_limit)
            if monthly_cost_limit is not None and hasattr(user, "monthly_cost_limit"):
                user.monthly_cost_limit = float(monthly_cost_limit)
            if storage_limit_bytes is not None and hasattr(user, "storage_limit_bytes"):
                user.storage_limit_bytes = int(storage_limit_bytes)
            if plan is not None and hasattr(user, "plan"):
                user.plan = str(plan).strip().lower()[:30]
            db.commit()
            return self._snapshot(user_id)
        finally:
            db.close()

    def admin_reset_usage(self, user_id: int) -> dict[str, Any]:
        db = self.SessionLocal()
        try:
            user = db.get(self.User, user_id)
            if not user:
                raise ValueError("user_not_found")
            user.monthly_token_used = 0
            if hasattr(user, "monthly_cost_used"):
                user.monthly_cost_used = 0
            user.quota_reset_at = self._now() + self.quota_service.RESET_PERIOD
            db.commit()
            return self._snapshot(user_id)
        finally:
            db.close()

    def get_usage_for_user(self, user_id: int) -> dict[str, Any]:
        snap = self._snapshot(user_id)
        percent = (
            round(100.0 * snap["token_used"] / snap["token_limit"], 2)
            if snap["token_limit"]
            else 0.0
        )
        return {
            **self.quota_service.get_usage_summary(user_id),
            "plan": snap["plan"],
            "tokens": {
                "used": snap["token_used"],
                "limit": snap["token_limit"],
                "remaining": snap["remaining"],
                "percent": percent,
                "reset_at": snap["reset_at"],
                "warning": percent >= WARN_RATIO * 100,
            },
            "quotas_disabled": self.quotas_disabled(),
            "operations": [
                {**get_operation(k), "id": k} for k in _operation_ids()
            ],
        }

    def analytics(self, *, days: int = 30, limit: int = 50) -> dict[str, Any]:
        """Ops view: consumption by operation / user."""
        days = max(1, min(int(days or 30), 365))
        since = self._now().timestamp() - days * 86400
        since_dt = datetime.fromtimestamp(since, tz=timezone.utc)
        db = self.SessionLocal()
        try:
            q = self.select(self.UsageLog).where(self.UsageLog.created_at >= since_dt)
            rows = db.execute(q.limit(20_000)).scalars().all()
            by_op: dict[str, int] = {}
            by_user: dict[int, int] = {}
            total = 0
            for r in rows:
                op = getattr(r, "operation", None) or r.action or "unknown"
                amt = int(r.amount or 0)
                by_op[op] = by_op.get(op, 0) + amt
                by_user[int(r.user_id)] = by_user.get(int(r.user_id), 0) + amt
                total += amt
            top_ops = sorted(by_op.items(), key=lambda x: -x[1])[:limit]
            top_users = sorted(by_user.items(), key=lambda x: -x[1])[:limit]
            return {
                "days": days,
                "total_units": total,
                "by_operation": [{"operation": k, "units": v} for k, v in top_ops],
                "by_user": [{"user_id": k, "units": v} for k, v in top_users],
            }
        finally:
            db.close()


def _operation_ids():
    from quotas.operations import OPERATIONS

    return list(OPERATIONS.keys())
