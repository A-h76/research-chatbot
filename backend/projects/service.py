"""ProjectService — ownership, hub read model, and project questions CRUD.

The hub (``get_hub``) is the single initial payload for the Project Workspace.
Tabs lazy-load deeper lists only when opened; Overview must not fan out to
five endpoints on mount.

Factory pattern: never ``import server``. Callers inject SessionLocal + models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

# Hub list caps — keep the first paint small.
_RECENT_PAPERS = 8
_RECENT_NOTES = 5
_RECENT_INSIGHTS = 5
_OPEN_QUESTIONS_HUB = 8
_UNREAD_ACTIVITY = 8

_QUESTION_STATUSES = frozenset({"open", "answered", "parked"})
_QUESTION_SOURCES = frozenset({"manual", "ai"})
_QUESTION_TEXT_MAX = 2000


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


@dataclass
class ProjectService:
    """Project workspace operations against injected SQLAlchemy models."""

    SessionLocal: Callable[[], Any]
    select: Any
    Project: Any
    UserFile: Any
    Note: Any
    Memory: Any
    Conversation: Any
    DerivedAnalysis: Any
    ProjectQuestion: Any
    AnalysisPipelineResult: Any | None = None
    PaperAnalysis: Any | None = None

    def get_owned(self, db: Any, project_id: int, user_id: int) -> Any | None:
        p = db.get(self.Project, project_id)
        if not p or p.user_id != user_id:
            return None
        return p

    def serialize_project(self, p: Any) -> dict[str, Any]:
        return {
            "id": p.id,
            "name": p.name,
            "emoji": p.emoji or "📁",
            "description": p.description or "",
            "instructions": p.instructions or "",
            "created_at": _iso(getattr(p, "created_at", None)),
        }

    def _paper_brief(self, f: Any) -> dict[str, Any]:
        return {
            "id": f.id,
            "name": f.name,
            "title": f.title or "",
            "authors": f.authors or "",
            "year": f.year or "",
            "reading_status": f.reading_status or "unread",
            "meta_status": f.meta_status or "pending",
            "created_at": _iso(getattr(f, "created_at", None)),
        }

    def _note_brief(self, n: Any) -> dict[str, Any]:
        content = n.content or ""
        return {
            "id": n.id,
            "title": n.title or "",
            "content_preview": content[:180],
            "file_id": n.file_id,
            "updated_at": _iso(getattr(n, "updated_at", None)),
        }

    def _insight_brief(self, d: Any) -> dict[str, Any]:
        """Insights = AI-derived compare/gaps/research (not user notes)."""
        if d.kind == "research":
            title = "Project research"
        elif d.kind == "compare":
            title = "Comparison"
        else:
            title = "Gap analysis"
        try:
            import json

            if d.kind == "research" and d.data:
                payload = json.loads(d.data)
                if isinstance(payload, dict):
                    preset = payload.get("preset") or ""
                    labels = {
                        "evidence": "Summarise the evidence",
                        "disagree": "Where papers disagree",
                        "methodology": "Compare methodologies",
                        "open_questions": "Open questions",
                        "compare": "Compare papers",
                        "datasets": "Compare datasets",
                    }
                    if preset in labels:
                        title = labels[preset]
                    elif payload.get("query"):
                        title = str(payload["query"])[:80]
                    elif payload.get("summary"):
                        title = str(payload["summary"])[:80]
            ids = json.loads(d.file_ids or "[]")
            n = len(ids) if isinstance(ids, list) else 0
            if n and d.kind != "research":
                title = f"{title} · {n} papers"
        except Exception:
            pass
        return {
            "id": d.id,
            "kind": d.kind,
            "title": title,
            "created_at": _iso(getattr(d, "created_at", None)),
        }

    def serialize_question(self, q: Any) -> dict[str, Any]:
        return {
            "id": q.id,
            "project_id": q.project_id,
            "text": q.text or "",
            "status": q.status or "open",
            "source": q.source or "manual",
            "linked_insight_id": q.linked_insight_id,
            "created_at": _iso(getattr(q, "created_at", None)),
            "updated_at": _iso(getattr(q, "updated_at", None)),
        }

    def _insight_detail(self, d: Any) -> dict[str, Any]:
        """Full insight row for lazy-loaded Insights tab."""
        import json

        brief = self._insight_brief(d)
        preview = ""
        file_ids: list[int] = []
        try:
            file_ids = json.loads(d.file_ids or "[]")
            if not isinstance(file_ids, list):
                file_ids = []
        except Exception:
            file_ids = []
        try:
            payload = json.loads(d.data or "{}") if d.data else {}
            if isinstance(payload, dict):
                preview = (
                    str(
                        payload.get("summary")
                        or payload.get("overview")
                        or payload.get("preamble")
                        or payload.get("synthesis")
                        or payload.get("answer")
                        or ""
                    )
                )[:280]
        except Exception:
            pass
        return {
            **brief,
            "file_ids": file_ids,
            "preview": preview,
            "model": getattr(d, "model", "") or "",
        }

    def list_insights(self, project_id: int, user_id: int) -> dict[str, Any] | None:
        """Lazy-loaded full insights list for the Insights tab."""
        db = self.SessionLocal()
        try:
            if self.get_owned(db, project_id, user_id) is None:
                return None
            rows = (
                db.execute(
                    self.select(self.DerivedAnalysis)
                    .where(
                        self.DerivedAnalysis.user_id == user_id,
                        self.DerivedAnalysis.project_id == project_id,
                    )
                    .order_by(self.DerivedAnalysis.created_at.desc())
                )
                .scalars()
                .all()
            )
            items = [self._insight_detail(d) for d in rows]
            return {"items": items, "total": len(items)}
        finally:
            db.close()

    def get_hub(self, project_id: int, user_id: int) -> dict[str, Any] | None:
        """Single read model for Project Workspace initial load."""
        db = self.SessionLocal()
        try:
            p = self.get_owned(db, project_id, user_id)
            if p is None:
                return None

            papers = (
                db.execute(
                    self.select(self.UserFile)
                    .where(
                        self.UserFile.user_id == user_id,
                        self.UserFile.project_id == project_id,
                        self.UserFile.kind == "document",
                    )
                    .order_by(self.UserFile.created_at.desc())
                )
                .scalars()
                .all()
            )

            notes = (
                db.execute(
                    self.select(self.Note)
                    .where(
                        self.Note.user_id == user_id,
                        self.Note.project_id == project_id,
                    )
                    .order_by(self.Note.updated_at.desc())
                )
                .scalars()
                .all()
            )

            chats = (
                db.execute(
                    self.select(self.Conversation).where(
                        self.Conversation.user_id == user_id,
                        self.Conversation.project_id == project_id,
                    )
                )
                .scalars()
                .all()
            )

            memories = (
                db.execute(
                    self.select(self.Memory).where(
                        self.Memory.user_id == user_id,
                        self.Memory.project_id == project_id,
                    )
                )
                .scalars()
                .all()
            )

            insights = (
                db.execute(
                    self.select(self.DerivedAnalysis)
                    .where(
                        self.DerivedAnalysis.user_id == user_id,
                        self.DerivedAnalysis.project_id == project_id,
                    )
                    .order_by(self.DerivedAnalysis.created_at.desc())
                )
                .scalars()
                .all()
            )
            insights_recent = insights[:_RECENT_INSIGHTS]

            all_questions = (
                db.execute(
                    self.select(self.ProjectQuestion)
                    .where(
                        self.ProjectQuestion.user_id == user_id,
                        self.ProjectQuestion.project_id == project_id,
                    )
                    .order_by(self.ProjectQuestion.updated_at.desc())
                )
                .scalars()
                .all()
            )
            open_qs = [q for q in all_questions if (q.status or "open") == "open"]

            rs_counts = {"unread": 0, "reading": 0, "read": 0}
            pipeline = {"done": 0, "running": 0, "pending": 0, "failed": 0, "partial": 0}
            analysis_pipeline = {"ready": 0, "running": 0, "pending": 0, "failed": 0}
            cross_paper_ready = 0
            analysis_status_map: dict[int, str] = {}
            if self.PaperAnalysis is not None and papers:
                from backend.library.paper_analysis import (
                    batch_paper_analysis_status,
                    cross_paper_research_ready,
                )

                analysis_status_map = batch_paper_analysis_status(
                    db,
                    [f.id for f in papers],
                    self.PaperAnalysis,
                    self.select,
                )
            for f in papers:
                rs = f.reading_status or "unread"
                if rs in rs_counts:
                    rs_counts[rs] += 1
                ms = f.meta_status or "pending"
                if ms in pipeline:
                    pipeline[ms] += 1
                else:
                    pipeline["pending"] += 1
                pa_status = analysis_status_map.get(f.id, "pending")
                if pa_status == "done":
                    analysis_pipeline["ready"] += 1
                elif pa_status in analysis_pipeline:
                    analysis_pipeline[pa_status] += 1
                else:
                    analysis_pipeline["pending"] += 1
                if cross_paper_research_ready(pa_status):
                    cross_paper_ready += 1

            open_questions = [self.serialize_question(q) for q in open_qs[:_OPEN_QUESTIONS_HUB]]
            recent_papers = [self._paper_brief(f) for f in papers[:_RECENT_PAPERS]]
            recent_notes = [self._note_brief(n) for n in notes[:_RECENT_NOTES]]
            recent_insights = [self._insight_brief(d) for d in insights_recent]

            unread_activity: list[dict[str, Any]] = []
            for q in open_qs:
                unread_activity.append(
                    {
                        "kind": "question_open",
                        "id": q.id,
                        "title": (q.text or "")[:120],
                        "at": _iso(getattr(q, "updated_at", None)),
                    }
                )
                if len(unread_activity) >= _UNREAD_ACTIVITY:
                    break
            for f in papers:
                if len(unread_activity) >= _UNREAD_ACTIVITY:
                    break
                if (f.reading_status or "unread") != "unread":
                    continue
                unread_activity.append(
                    {
                        "kind": "paper_unread",
                        "id": f.id,
                        "title": f.title or f.name,
                        "at": _iso(getattr(f, "created_at", None)),
                    }
                )
            if len(unread_activity) < _UNREAD_ACTIVITY:
                for d in insights:
                    unread_activity.append(
                        {
                            "kind": "insight",
                            "id": d.id,
                            "title": self._insight_brief(d)["title"],
                            "at": _iso(getattr(d, "created_at", None)),
                        }
                    )
                    if len(unread_activity) >= _UNREAD_ACTIVITY:
                        break

            return {
                "project": self.serialize_project(p),
                "stats": {
                    "papers": len(papers),
                    "chats": len(chats),
                    "memories": len(memories),
                    "notes": len(notes),
                    "open_questions": len(open_qs),
                    "insights": len(insights),
                    "unread": rs_counts["unread"],
                    "reading": rs_counts["reading"],
                    "read": rs_counts["read"],
                    "cross_paper_ready": cross_paper_ready,
                },
                "recent_papers": recent_papers,
                "recent_notes": recent_notes,
                "open_questions": open_questions,
                "recent_insights": recent_insights,
                "pipeline_summary": pipeline,
                "analysis_summary": analysis_pipeline,
                "unread_activity": unread_activity,
            }
        finally:
            db.close()

    def get_detail(self, project_id: int, user_id: int) -> dict[str, Any] | None:
        """Legacy detail shape (stats only) — prefer ``get_hub`` for the workspace."""
        hub = self.get_hub(project_id, user_id)
        if hub is None:
            return None
        p = hub["project"]
        s = hub["stats"]
        return {
            "id": p["id"],
            "name": p["name"],
            "emoji": p["emoji"],
            "description": p["description"],
            "instructions": p["instructions"],
            "created_at": p["created_at"],
            "stats": {
                "papers": s["papers"],
                "chats": s["chats"],
                "memories": s["memories"],
                "unread": s["unread"],
                "reading": s["reading"],
                "read": s["read"],
            },
        }

    # ── Questions CRUD ────────────────────────────────────────────────────

    def list_questions(
        self,
        project_id: int,
        user_id: int,
        *,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        db = self.SessionLocal()
        try:
            if self.get_owned(db, project_id, user_id) is None:
                return None
            stmt = (
                self.select(self.ProjectQuestion)
                .where(
                    self.ProjectQuestion.user_id == user_id,
                    self.ProjectQuestion.project_id == project_id,
                )
                .order_by(self.ProjectQuestion.updated_at.desc())
            )
            rows = db.execute(stmt).scalars().all()
            if status and status in _QUESTION_STATUSES:
                rows = [q for q in rows if (q.status or "open") == status]
            return {
                "items": [self.serialize_question(q) for q in rows],
                "total": len(rows),
            }
        finally:
            db.close()

    def create_question(
        self,
        project_id: int,
        user_id: int,
        *,
        text: str,
        status: str = "open",
        source: str = "manual",
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Returns (payload, error_code). error_code is None on success."""
        cleaned = (text or "").strip()
        if not cleaned:
            return None, "text_required"
        if len(cleaned) > _QUESTION_TEXT_MAX:
            cleaned = cleaned[:_QUESTION_TEXT_MAX]
        if status not in _QUESTION_STATUSES:
            status = "open"
        if source not in _QUESTION_SOURCES:
            source = "manual"

        db = self.SessionLocal()
        try:
            if self.get_owned(db, project_id, user_id) is None:
                return None, "not_found"
            q = self.ProjectQuestion(
                user_id=user_id,
                project_id=project_id,
                text=cleaned,
                status=status,
                source=source,
            )
            db.add(q)
            db.commit()
            db.refresh(q)
            return self.serialize_question(q), None
        finally:
            db.close()

    def update_question(
        self,
        project_id: int,
        question_id: int,
        user_id: int,
        *,
        text: str | None = None,
        status: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        db = self.SessionLocal()
        try:
            if self.get_owned(db, project_id, user_id) is None:
                return None, "not_found"
            q = db.get(self.ProjectQuestion, question_id)
            if not q or q.user_id != user_id or q.project_id != project_id:
                return None, "not_found"
            if text is not None:
                cleaned = text.strip()
                if not cleaned:
                    return None, "text_required"
                q.text = cleaned[:_QUESTION_TEXT_MAX]
            if status is not None:
                if status not in _QUESTION_STATUSES:
                    return None, "invalid_status"
                q.status = status
            q.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(q)
            return self.serialize_question(q), None
        finally:
            db.close()

    def delete_question(
        self, project_id: int, question_id: int, user_id: int
    ) -> str | None:
        """Returns error_code or None on success."""
        db = self.SessionLocal()
        try:
            if self.get_owned(db, project_id, user_id) is None:
                return "not_found"
            q = db.get(self.ProjectQuestion, question_id)
            if not q or q.user_id != user_id or q.project_id != project_id:
                return "not_found"
            db.delete(q)
            db.commit()
            return None
        finally:
            db.close()


def create_project_service(
    *,
    SessionLocal,
    select,
    Project,
    UserFile,
    Note,
    Memory,
    Conversation,
    DerivedAnalysis,
    ProjectQuestion,
    AnalysisPipelineResult=None,
    PaperAnalysis=None,
) -> ProjectService:
    return ProjectService(
        SessionLocal=SessionLocal,
        select=select,
        Project=Project,
        UserFile=UserFile,
        Note=Note,
        Memory=Memory,
        Conversation=Conversation,
        DerivedAnalysis=DerivedAnalysis,
        ProjectQuestion=ProjectQuestion,
        AnalysisPipelineResult=AnalysisPipelineResult,
        PaperAnalysis=PaperAnalysis,
    )
