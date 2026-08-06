"""Library overview routes extracted from server.py.

Includes list/tags/stats/dashboard surfaces used by Library and Dashboard UI.
Behavior is kept identical; this is a boundary refactor only.
"""

from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, jsonify, request, session


def create_library_overview_blueprint(
    *,
    SessionLocal,
    UserFile,
    PaperAnalysis,
    Conversation,
    Citation,
    Project,
    select_fn,
    login_required,
    file_to_dict,
    collection_service,
):
    bp = Blueprint("library_overview", __name__)

    @bp.get("/api/files")
    @login_required
    def list_files():
        from backend.library.search import params_from_request, search_library

        uid = session["user_id"]
        params = params_from_request(request.args, uid)
        if params.collection_id:
            file_ids = collection_service.file_ids_in_collection(uid, params.collection_id)
            if file_ids is None:
                return jsonify({"error": "collection_not_found"}), 404
            params.file_ids = file_ids
        db = SessionLocal()
        try:
            from backend.library.paper_analysis import (
                batch_paper_analysis_status,
                enrich_file_payload,
            )

            total, page = search_library(db, UserFile, params)
            status_map = batch_paper_analysis_status(
                db,
                [x.id for x in page],
                PaperAnalysis,
                select_fn,
            )
            items = [
                enrich_file_payload(file_to_dict(x), status_map.get(x.id, "pending"))
                for x in page
            ]
            return jsonify(
                {
                    "total": total,
                    "offset": params.offset,
                    "limit": params.limit,
                    "items": items,
                }
            )
        finally:
            db.close()

    @bp.get("/api/library/tags")
    @login_required
    def library_tags():
        uid = session["user_id"]
        project_id_raw = request.args.get("project_id")
        db = SessionLocal()
        try:
            q_stmt = select_fn(UserFile).where(
                UserFile.user_id == uid,
                UserFile.tags.isnot(None),
            )
            if project_id_raw is not None:
                try:
                    pid = int(project_id_raw)
                    q_stmt = q_stmt.where(UserFile.project_id == pid if pid else UserFile.project_id.is_(None))
                except (TypeError, ValueError):
                    pass

            files = db.execute(q_stmt).scalars().all()
            counts: dict[str, int] = {}
            for f in files:
                try:
                    for t in json.loads(f.tags or "[]"):
                        if t:
                            counts[t] = counts.get(t, 0) + 1
                except Exception:
                    pass

            result = sorted(
                [{"tag": t, "count": c} for t, c in counts.items()],
                key=lambda x: -x["count"],
            )
            return jsonify(result)
        finally:
            db.close()

    @bp.get("/api/library/stats")
    @login_required
    def library_stats():
        uid = session["user_id"]
        project_id_raw = request.args.get("project_id")
        db = SessionLocal()
        try:
            q_stmt = select_fn(UserFile).where(UserFile.user_id == uid)
            if project_id_raw is not None:
                try:
                    pid = int(project_id_raw)
                    q_stmt = q_stmt.where(UserFile.project_id == pid if pid else UserFile.project_id.is_(None))
                except (TypeError, ValueError):
                    pass

            files = db.execute(q_stmt).scalars().all()
            docs = [f for f in files if f.kind == "document"]
            images = [f for f in files if f.kind == "image"]

            rs_counts: dict[str, int] = {"unread": 0, "reading": 0, "read": 0}
            tag_counts: dict[str, int] = {}
            for f in docs:
                rs = f.reading_status or "unread"
                if rs in rs_counts:
                    rs_counts[rs] += 1
                try:
                    for t in json.loads(f.tags or "[]"):
                        if t:
                            tag_counts[t] = tag_counts.get(t, 0) + 1
                except Exception:
                    pass

            doc_ids = [f.id for f in docs]
            analyses_done = 0
            analyses_pending = 0
            if doc_ids:
                pas = db.execute(select_fn(PaperAnalysis).where(PaperAnalysis.file_id.in_(doc_ids))).scalars().all()
                analyses_done = sum(1 for p in pas if p.status == "done")
                analyses_pending = sum(1 for p in pas if p.status in ("pending", "running"))

            top_tags = sorted(
                [{"tag": t, "count": c} for t, c in tag_counts.items()],
                key=lambda x: -x["count"],
            )[:5]

            return jsonify(
                {
                    "total_papers": len(docs),
                    "total_images": len(images),
                    "unread": rs_counts["unread"],
                    "reading": rs_counts["reading"],
                    "read": rs_counts["read"],
                    "analysis_done": analyses_done,
                    "analysis_pending": analyses_pending,
                    "top_tags": top_tags,
                }
            )
        finally:
            db.close()

    @bp.get("/api/dashboard")
    @login_required
    def dashboard():
        uid = session["user_id"]
        db = SessionLocal()
        try:
            all_files = db.execute(select_fn(UserFile).where(UserFile.user_id == uid)).scalars().all()
            docs = [f for f in all_files if f.kind == "document"]
            rs_cnt = {"unread": 0, "reading": 0, "read": 0}
            tag_cnt: dict[str, int] = {}
            for f in docs:
                rs = f.reading_status or "unread"
                if rs in rs_cnt:
                    rs_cnt[rs] += 1
                try:
                    for t in json.loads(f.tags or "[]"):
                        if t:
                            tag_cnt[t] = tag_cnt.get(t, 0) + 1
                except Exception:
                    pass

            def _paper_brief(f):
                return {
                    "id": f.id,
                    "name": f.name,
                    "title": f.title or "",
                    "authors": f.authors or "",
                    "year": f.year or "",
                    "reading_status": f.reading_status or "unread",
                    "meta_status": f.meta_status or "pending",
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }

            sorted_docs = sorted(docs, key=lambda f: f.created_at or datetime.min, reverse=True)
            recent_papers = [_paper_brief(f) for f in sorted_docs[:5]]
            current_papers = [_paper_brief(f) for f in sorted_docs if (f.reading_status or "unread") == "reading"][:5]

            top_tags = sorted(
                [{"tag": t, "count": c} for t, c in tag_cnt.items()],
                key=lambda x: -x["count"],
            )[:5]

            analysed = sum(1 for f in docs if (f.meta_status or "") == "done")
            processing = sum(1 for f in docs if (f.meta_status or "") in ("pending", "running"))
            library = {
                "total_papers": len(docs),
                "unread": rs_cnt["unread"],
                "reading": rs_cnt["reading"],
                "read": rs_cnt["read"],
                "analysed": analysed,
                "processing": processing,
                "top_tags": top_tags,
            }

            convos = (
                db.execute(select_fn(Conversation).where(Conversation.user_id == uid).order_by(Conversation.updated_at.desc()))
                .scalars()
                .all()
            )
            recent_chats = [
                {
                    "id": c.id,
                    "title": c.title or "Untitled chat",
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                    "file_id": c.file_id,
                    "project_id": c.project_id,
                }
                for c in convos[:5]
            ]

            cites = (
                db.execute(select_fn(Citation).where(Citation.user_id == uid).order_by(Citation.created_at.desc()))
                .scalars()
                .all()
            )
            recent_citations = [{"id": c.id, "title": c.title, "authors": c.authors, "year": c.year} for c in cites[:5]]

            projects = db.execute(select_fn(Project).where(Project.user_id == uid)).scalars().all()
            file_proj_cnt = {}
            for f in docs:
                if f.project_id:
                    file_proj_cnt[f.project_id] = file_proj_cnt.get(f.project_id, 0) + 1
            convo_proj_cnt = {}
            for c in convos:
                if c.project_id:
                    convo_proj_cnt[c.project_id] = convo_proj_cnt.get(c.project_id, 0) + 1

            projects_out = [
                {
                    "id": p.id,
                    "name": p.name,
                    "emoji": p.emoji,
                    "paper_count": file_proj_cnt.get(p.id, 0),
                    "chat_count": convo_proj_cnt.get(p.id, 0),
                }
                for p in projects
            ]

            return jsonify(
                {
                    "library": library,
                    "recent_papers": recent_papers,
                    "current_papers": current_papers,
                    "recent_chats": recent_chats,
                    "recent_citations": recent_citations,
                    "projects": projects_out,
                }
            )
        finally:
            db.close()

    return bp
