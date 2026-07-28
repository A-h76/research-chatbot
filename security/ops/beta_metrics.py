"""Closed-beta KPI aggregation for admin validation (Phase 0)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select


class BetaMetricsService:
    """SQL-backed beta funnel — no separate event pipeline for Phase 0."""

    def __init__(
        self,
        SessionLocal,
        User,
        Project,
        UserFile,
        DerivedAnalysis,
        Memory,
        select_fn,
        *,
        now_fn=None,
    ):
        self.SessionLocal = SessionLocal
        self.User = User
        self.Project = Project
        self.UserFile = UserFile
        self.DerivedAnalysis = DerivedAnalysis
        self.Memory = Memory
        self.select = select_fn
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def _since(self, days: int) -> datetime:
        return self._now() - timedelta(days=days)

    @staticmethod
    def _naive(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.replace(tzinfo=None)

    def snapshot(self, *, days: int = 7) -> dict[str, Any]:
        since = self._since(days)
        since_cmp = self._naive(since)
        db = self.SessionLocal()
        try:
            new_users = db.execute(
                select(func.count()).select_from(self.User).where(self.User.created_at >= since_cmp)
            ).scalar() or 0

            returning_users = db.execute(
                select(func.count())
                .select_from(self.User)
                .where(self.User.last_login_at.isnot(None))
                .where(self.User.last_login_at >= since_cmp)
            ).scalar() or 0

            new_projects = db.execute(
                select(func.count()).select_from(self.Project).where(self.Project.created_at >= since_cmp)
            ).scalar() or 0

            papers_analysed = db.execute(
                select(func.count())
                .select_from(self.UserFile)
                .where(self.UserFile.meta_status == "done")
                .where(self.UserFile.created_at >= since_cmp)
            ).scalar() or 0

            research_runs = db.execute(
                select(func.count())
                .select_from(self.DerivedAnalysis)
                .where(self.DerivedAnalysis.kind == "research")
                .where(self.DerivedAnalysis.created_at >= since_cmp)
            ).scalar() or 0

            memories_promoted = db.execute(
                select(func.count())
                .select_from(self.Memory)
                .where(self.Memory.source == "research")
                .where(self.Memory.created_at >= since_cmp)
            ).scalar() or 0

            # Activation funnel (all-time snapshot)
            users_with_projects = db.execute(
                select(func.count(func.distinct(self.Project.user_id)))
            ).scalar() or 0

            subq = (
                select(self.UserFile.user_id)
                .where(self.UserFile.meta_status == "done")
                .where(self.UserFile.project_id.isnot(None))
                .group_by(self.UserFile.user_id)
                .having(func.count(self.UserFile.id) >= 2)
                .subquery()
            )
            activated_users = db.execute(select(func.count()).select_from(subq)).scalar() or 0

            research_users = db.execute(
                select(func.count(func.distinct(self.DerivedAnalysis.user_id))).where(
                    self.DerivedAnalysis.kind == "research"
                )
            ).scalar() or 0

            return {
                "period_days": days,
                "since": since.isoformat(),
                "counts": {
                    "new_users": int(new_users),
                    "returning_users": int(returning_users),
                    "new_projects": int(new_projects),
                    "papers_analysed": int(papers_analysed),
                    "research_runs": int(research_runs),
                    "memories_promoted": int(memories_promoted),
                },
                "funnel_all_time": {
                    "users_with_projects": int(users_with_projects),
                    "users_2plus_analysed_papers": int(activated_users),
                    "users_with_research_run": int(research_users),
                },
                "targets": {
                    "activation": "project + 2 analysed papers + 1 research run",
                    "retention": "returning_users within period",
                },
            }
        finally:
            db.close()


def record_last_login(SessionLocal, User, user_id: int, *, now_fn=None) -> None:
    now = (now_fn or (lambda: datetime.now(timezone.utc)))()
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            return
        user.last_login_at = now
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
