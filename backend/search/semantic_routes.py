"""Session-auth unified semantic search extracted from server.py (Phase 3).

JWT counterparts remain in backend/search/routes.py (/api/documents/search, /api/rag).
Shared retrieval helpers live in backend/search/shared.py.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from backend.search.shared import keyword_score, search_user_document_chunks


def create_semantic_search_blueprint(
    *,
    SessionLocal,
    UserFile,
    Chunk,
    Note,
    Citation,
    Message,
    Conversation,
    select_fn,
    login_required,
    limiter,
    embed_texts,
):
    bp = Blueprint("semantic_search_routes", __name__)

    @bp.route("/api/search", methods=["POST"])
    @login_required
    @limiter.limit("60 per minute")
    def semantic_search():
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        q = str(data.get("q") or "").strip()
        kinds = data.get("kinds") or ["paper", "note", "citation", "chat"]
        project_id = data.get("project_id")
        try:
            limit = max(1, min(50, int(data.get("limit", 20))))
        except (TypeError, ValueError):
            limit = 20

        if len(q) < 2:
            return (
                jsonify(
                    {
                        "error": "query_too_short",
                        "detail": "Query must be at least 2 characters.",
                    }
                ),
                400,
            )

        query_emb = None
        try:
            query_emb = embed_texts([q])[0]
        except Exception:
            pass

        results = []
        db = SessionLocal()
        try:
            if "paper" in kinds:
                file_stmt = select_fn(UserFile).where(
                    UserFile.user_id == uid,
                    UserFile.kind == "document",
                )
                if project_id is not None:
                    file_stmt = file_stmt.where(UserFile.project_id == project_id)
                files = db.execute(file_stmt).scalars().all()
                file_ids = [f.id for f in files]

                if file_ids:
                    for score, ch, uf in search_user_document_chunks(
                        db,
                        UserFile=UserFile,
                        Chunk=Chunk,
                        select=select_fn,
                        user_id=uid,
                        query_embedding=query_emb,
                        query_text=q,
                        project_id=project_id,
                        limit=10000,
                        min_score=0.15,
                        allow_keyword_fallback=True,
                    ):
                        title = (uf.title or uf.name) if uf else "Paper"
                        results.append(
                            {
                                "kind": "paper",
                                "ref_id": ch.file_id,
                                "chunk_id": ch.id,
                                "title": title,
                                "snippet": ch.content[:300],
                                "score": round(score, 4),
                                "url": f"/papers/{ch.file_id}",
                                "page": ch.page,
                                "section": ch.section,
                                "file_name": uf.name if uf else None,
                            }
                        )

            if "note" in kinds:
                note_stmt = select_fn(Note).where(Note.user_id == uid)
                if project_id is not None:
                    note_stmt = note_stmt.where(Note.project_id == project_id)
                notes = db.execute(note_stmt).scalars().all()
                for n in notes:
                    text = (n.title or "") + " " + (n.content or "")
                    score = keyword_score(q, text)
                    if score < 0.20:
                        continue
                    results.append(
                        {
                            "kind": "note",
                            "ref_id": n.id,
                            "title": n.title or "Untitled note",
                            "snippet": (n.content or "")[:300],
                            "score": round(score, 4),
                            "url": "/notes",
                            "page": None,
                            "section": None,
                            "file_name": None,
                        }
                    )

            if "citation" in kinds:
                cit_stmt = select_fn(Citation).where(Citation.user_id == uid)
                if project_id is not None:
                    cit_stmt = cit_stmt.where(Citation.project_id == project_id)
                cits = db.execute(cit_stmt).scalars().all()
                for c in cits:
                    text = " ".join(filter(None, [c.title, c.authors, c.venue, c.notes]))
                    score = keyword_score(q, text)
                    if score < 0.20:
                        continue
                    results.append(
                        {
                            "kind": "citation",
                            "ref_id": c.id,
                            "title": c.title or "Untitled",
                            "snippet": f"{c.authors} ({c.year}) — {c.venue}".strip(" —"),
                            "score": round(score, 4),
                            "url": "/citations",
                            "page": None,
                            "section": None,
                            "file_name": None,
                        }
                    )

            if "chat" in kinds:
                msg_stmt = (
                    select_fn(Message, Conversation)
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .where(
                        Conversation.user_id == uid,
                        Message.role == "assistant",
                    )
                )
                if project_id is not None:
                    msg_stmt = msg_stmt.where(Conversation.project_id == project_id)
                rows = db.execute(msg_stmt.limit(2000)).all()
                seen_convos: set[int] = set()
                for msg, convo in rows:
                    if convo.id in seen_convos:
                        continue
                    score = keyword_score(q, msg.content or "")
                    if score < 0.25:
                        continue
                    seen_convos.add(convo.id)
                    results.append(
                        {
                            "kind": "chat",
                            "ref_id": convo.id,
                            "title": convo.title or "Untitled chat",
                            "snippet": (msg.content or "")[:300],
                            "score": round(score, 4),
                            "url": f"/c/{convo.id}",
                            "page": None,
                            "section": None,
                            "file_name": None,
                        }
                    )

        finally:
            db.close()

        results.sort(key=lambda r: -r["score"])
        seen_papers: set[int] = set()
        deduped = []
        for r in results:
            if r["kind"] == "paper":
                if r["ref_id"] in seen_papers:
                    continue
                seen_papers.add(r["ref_id"])
            deduped.append(r)

        return jsonify(
            {
                "q": q,
                "total": len(deduped),
                "results": deduped[:limit],
            }
        )

    return bp
