"""Load Research State from DB signals (factory / DI — never import server)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_

from backend.assistant.research_state import (
    CorpusSignals,
    ProjectSignals,
    ResearchState,
    WritingSignals,
    build_research_state,
    user_signals_from_orm,
)
from backend.evidence.objects import serialize_evidence_object
from backend.evidence.themes import discover_themes
from backend.evidence.gaps import discover_gaps


def create_research_state_service(
    *,
    SessionLocal: Any,
    User: Any,
    Project: Any,
    UserFile: Any,
    EvidenceObject: Any,
    WritingDocument: Any | None,
    select: Any,
):
    """Return a callable ``get_research_state(user_id, project_id=None) -> ResearchState``."""

    def _count_papers(db, user_id: int, project_id: int) -> int:
        return int(
            db.execute(
                select(func.count())
                .select_from(UserFile)
                .where(
                    UserFile.user_id == user_id,
                    UserFile.project_id == project_id,
                    UserFile.kind == "document",
                )
            ).scalar()
            or 0
        )

    def _count_evidence(db, user_id: int, project_id: int) -> int:
        return int(
            db.execute(
                select(func.count())
                .select_from(EvidenceObject)
                .where(
                    EvidenceObject.user_id == user_id,
                    EvidenceObject.project_id == project_id,
                    EvidenceObject.status != "superseded",
                    EvidenceObject.status.in_(["candidate", "accepted"]),
                )
            ).scalar()
            or 0
        )

    def _papers_with_evidence(db, user_id: int, project_id: int) -> int:
        return int(
            db.execute(
                select(func.count(func.distinct(EvidenceObject.file_id)))
                .select_from(EvidenceObject)
                .where(
                    EvidenceObject.user_id == user_id,
                    EvidenceObject.project_id == project_id,
                    EvidenceObject.status != "superseded",
                    EvidenceObject.status.in_(["candidate", "accepted"]),
                )
            ).scalar()
            or 0
        )

    def _count_contradiction_rows(db, user_id: int, project_id: int) -> int:
        """Deterministic: evidence rows with a non-empty contradicts_json list."""
        rows = db.execute(
            select(EvidenceObject.contradicts_json).where(
                EvidenceObject.user_id == user_id,
                EvidenceObject.project_id == project_id,
                EvidenceObject.status != "superseded",
                EvidenceObject.status.in_(["candidate", "accepted"]),
                EvidenceObject.contradicts_json.isnot(None),
                EvidenceObject.contradicts_json != "",
                EvidenceObject.contradicts_json != "[]",
            )
        ).all()
        return len(rows)

    def _ri_theme_gap_counts(db, user_id: int, project_id: int) -> tuple[int, int]:
        """Optional RI builders over a capped corpus — still deterministic."""
        rows = list(
            db.execute(
                select(EvidenceObject)
                .where(
                    EvidenceObject.user_id == user_id,
                    EvidenceObject.project_id == project_id,
                    EvidenceObject.status != "superseded",
                    EvidenceObject.status.in_(["candidate", "accepted"]),
                )
                .order_by(EvidenceObject.id.asc())
                .limit(800)
            )
            .scalars()
            .all()
        )
        if not rows:
            return 0, 0
        objects = [serialize_evidence_object(r) for r in rows]
        file_ids = sorted({int(o["file_id"]) for o in objects if o.get("file_id") is not None})
        papers = [{"id": fid, "file_id": fid, "title": "", "name": "", "year": "", "authors": ""} for fid in file_ids]
        themes_payload = discover_themes(objects, project_id=project_id)
        theme_count = int((themes_payload.get("metrics") or {}).get("theme_count") or 0)
        gaps_payload = discover_gaps(
            project_id=project_id,
            papers=papers,
            evidence_objects=objects,
            themes_payload=themes_payload,
        )
        gap_count = int((gaps_payload.get("metrics") or {}).get("gap_count") or 0)
        return theme_count, gap_count

    def _writing_signals(db, user_id: int, project_id: int | None) -> WritingSignals:
        if WritingDocument is None or project_id is None:
            return WritingSignals()
        stmt = select(func.count()).select_from(WritingDocument).where(
            WritingDocument.user_id == user_id,
            WritingDocument.project_id == project_id,
        )
        # Exclude archived/deleted when columns exist
        status_col = getattr(WritingDocument, "status", None)
        if status_col is not None:
            stmt = stmt.where(
                or_(
                    WritingDocument.status.is_(None),
                    ~WritingDocument.status.in_(["archived", "deleted"]),
                )
            )
        n = int(db.execute(stmt).scalar() or 0)
        return WritingSignals(has_manuscript=n > 0, citation_count=0, review_complete=False)

    def get_research_state(user_id: int, project_id: int | None = None) -> ResearchState:
        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if user is None:
                raise LookupError("user_not_found")

            project_signals = ProjectSignals()
            corpus = CorpusSignals()
            writing = WritingSignals()

            # When no project is scoped, use the researcher's latest project so
            # Home + Mentor share one Research State (never invent different realities).
            resolved_id = int(project_id) if project_id is not None else None
            if resolved_id is None:
                order_col = getattr(Project, "created_at", Project.id)
                latest = db.execute(
                    select(Project)
                    .where(Project.user_id == user_id)
                    .order_by(order_col.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if latest is not None:
                    resolved_id = int(latest.id)

            if resolved_id is not None:
                proj = db.execute(
                    select(Project).where(Project.id == resolved_id, Project.user_id == user_id)
                ).scalar_one_or_none()
                if proj is None:
                    raise LookupError("project_not_found")
                project_signals = ProjectSignals(
                    id=int(proj.id),
                    title=(getattr(proj, "name", None) or "").strip() or None,
                    discipline=None,
                )
                papers = _count_papers(db, user_id, resolved_id)
                evidence = _count_evidence(db, user_id, resolved_id)
                pwe = _papers_with_evidence(db, user_id, resolved_id)
                coverage = round(pwe / papers, 4) if papers > 0 else None
                contradictions = _count_contradiction_rows(db, user_id, resolved_id)
                themes, gaps = (0, 0)
                if evidence > 0:
                    themes, gaps = _ri_theme_gap_counts(db, user_id, resolved_id)
                corpus = CorpusSignals(
                    papers=papers,
                    evidence=evidence,
                    themes=themes,
                    gaps=gaps,
                    contradictions=contradictions,
                    coverage=coverage,
                    unread=0,
                )
                writing = _writing_signals(db, user_id, resolved_id)

            return build_research_state(
                user=user_signals_from_orm(user),
                project=project_signals,
                corpus=corpus,
                writing=writing,
            )
        finally:
            db.close()

    return get_research_state
