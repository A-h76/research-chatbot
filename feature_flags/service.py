"""Runtime feature-flag evaluation against the ``feature_flags`` table.

Precedence:
1. Per-user row for (flag_name, user_id) if present
2. Global row (user_id IS NULL)
3. Registry default from ``flags.KNOWN_FLAGS`` (unknown flags → False)

When ``enabled`` is True and ``rollout_pct`` is set (0–100), membership is
deterministic via hash(flag_name, user_id) % 100 < rollout_pct. Without a
user_id, rollout_pct < 100 means denied (cannot place anonymous traffic in a
cohort safely).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from feature_flags.flags import KNOWN_FLAGS


class FeatureDisabled(Exception):
    """Raised by helpers when a gated path should return HTTP 503."""

    def __init__(self, flag_name: str, message: str | None = None):
        self.flag_name = flag_name
        self.message = message or f"Feature '{flag_name}' is temporarily disabled."
        super().__init__(self.message)


class FeatureFlagService:
    def __init__(self, SessionLocal, FeatureFlag, select):
        self.SessionLocal = SessionLocal
        self.FeatureFlag = FeatureFlag
        self.select = select

    def is_enabled(self, flag_name: str, user_id: int | None = None) -> bool:
        flag_name = (flag_name or "").strip()
        if not flag_name:
            return False

        db = self.SessionLocal()
        try:
            row = None
            if user_id is not None:
                row = db.execute(
                    self.select(self.FeatureFlag).where(
                        self.FeatureFlag.flag_name == flag_name,
                        self.FeatureFlag.user_id == int(user_id),
                    )
                ).scalar_one_or_none()
            if row is None:
                row = db.execute(
                    self.select(self.FeatureFlag).where(
                        self.FeatureFlag.flag_name == flag_name,
                        self.FeatureFlag.user_id.is_(None),
                    )
                ).scalar_one_or_none()

            if row is None:
                meta = KNOWN_FLAGS.get(flag_name)
                return bool(meta["default"]) if meta else False

            if not bool(row.enabled):
                return False

            pct = row.rollout_pct
            if pct is None:
                return True
            pct = max(0, min(100, int(pct)))
            if pct >= 100:
                return True
            if pct <= 0:
                return False
            if user_id is None:
                return False
            return self._in_rollout(flag_name, int(user_id), pct)
        finally:
            db.close()

    def require(self, flag_name: str, user_id: int | None = None) -> None:
        if not self.is_enabled(flag_name, user_id=user_id):
            raise FeatureDisabled(flag_name)

    @staticmethod
    def _in_rollout(flag_name: str, user_id: int, pct: int) -> bool:
        digest = hashlib.md5(f"{flag_name}:{user_id}".encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < pct

    def list_flags(self, *, include_defaults: bool = True) -> list[dict[str, Any]]:
        db = self.SessionLocal()
        try:
            rows = (
                db.execute(
                    self.select(self.FeatureFlag).order_by(
                        self.FeatureFlag.flag_name,
                        self.FeatureFlag.user_id,
                    )
                )
                .scalars()
                .all()
            )
            out = [self._row_dict(r) for r in rows]
            if include_defaults:
                present = {(r["flag_name"], r["user_id"]) for r in out}
                for name, meta in KNOWN_FLAGS.items():
                    if (name, None) not in present:
                        out.append(
                            {
                                "flag_name": name,
                                "enabled": bool(meta["default"]),
                                "user_id": None,
                                "rollout_pct": None,
                                "updated_at": None,
                                "source": "default",
                                "description": meta["description"],
                            }
                        )
            return out
        finally:
            db.close()

    def get_flag(
        self, flag_name: str, *, user_id: int | None = None
    ) -> dict[str, Any] | None:
        db = self.SessionLocal()
        try:
            q = self.select(self.FeatureFlag).where(self.FeatureFlag.flag_name == flag_name)
            if user_id is None:
                q = q.where(self.FeatureFlag.user_id.is_(None))
            else:
                q = q.where(self.FeatureFlag.user_id == int(user_id))
            row = db.execute(q).scalar_one_or_none()
            if row is not None:
                d = self._row_dict(row)
                d["source"] = "db"
                return d
            meta = KNOWN_FLAGS.get(flag_name)
            if meta and user_id is None:
                return {
                    "flag_name": flag_name,
                    "enabled": bool(meta["default"]),
                    "user_id": None,
                    "rollout_pct": None,
                    "updated_at": None,
                    "source": "default",
                    "description": meta["description"],
                }
            return None
        finally:
            db.close()

    def set_flag(
        self,
        flag_name: str,
        *,
        enabled: bool,
        user_id: int | None = None,
        rollout_pct: int | None = None,
    ) -> dict[str, Any]:
        flag_name = (flag_name or "").strip()
        if not flag_name:
            raise ValueError("flag_name is required")
        if rollout_pct is not None:
            rollout_pct = max(0, min(100, int(rollout_pct)))

        db = self.SessionLocal()
        try:
            q = self.select(self.FeatureFlag).where(self.FeatureFlag.flag_name == flag_name)
            if user_id is None:
                q = q.where(self.FeatureFlag.user_id.is_(None))
            else:
                q = q.where(self.FeatureFlag.user_id == int(user_id))
            row = db.execute(q).scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if row is None:
                row = self.FeatureFlag(
                    flag_name=flag_name,
                    enabled=bool(enabled),
                    user_id=int(user_id) if user_id is not None else None,
                    rollout_pct=rollout_pct,
                    updated_at=now,
                )
                db.add(row)
            else:
                row.enabled = bool(enabled)
                row.rollout_pct = rollout_pct
                row.updated_at = now
            db.commit()
            db.refresh(row)
            d = self._row_dict(row)
            d["source"] = "db"
            return d
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def evaluate_known(self, user_id: int | None = None) -> dict[str, bool]:
        return {name: self.is_enabled(name, user_id=user_id) for name in KNOWN_FLAGS}

    @staticmethod
    def _row_dict(row) -> dict[str, Any]:
        updated = getattr(row, "updated_at", None)
        return {
            "flag_name": row.flag_name,
            "enabled": bool(row.enabled),
            "user_id": row.user_id,
            "rollout_pct": row.rollout_pct,
            "updated_at": updated.isoformat() if updated is not None else None,
            "source": "db",
            "description": (KNOWN_FLAGS.get(row.flag_name) or {}).get("description"),
        }
