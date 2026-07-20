"""GET /api/documents/search and POST /api/rag — Bearer-JWT-authenticated
counterparts to server.py's existing session-based POST /api/search,
same relationship as /api/documents/upload has to /api/files: an
additional flow, not a replacement (see backend/upload/routes.py's own
docstring for the precedent this follows).

Deliberately does NOT duplicate /api/search's actual search logic or
introduce a second search "engine": both routes here search the exact
same Chunk.embedding data /api/search already uses for its paper results
(real cosine similarity — Chunk stores embeddings as JSON-serialized
floats, no pgvector extension needed, matching how /api/search has
worked all along). SearchIndex (the notes/citations/chat unified index)
is intentionally left untouched — nothing in this codebase has ever
written a row to it; reviving unpopulated schema wasn't asked for and
isn't needed for either route here, which only need paper chunks.

Constructor-injected (SessionLocal, models, utility_model), never
`import server` — same reason as every other module in auth/, quotas/,
and backend/: server.py runs as __main__, so a module it reaches into
importing "server" back re-executes the whole file under a second
module identity and recurses.
"""
import json
import math

from flask import Blueprint, request, jsonify, g
from sqlalchemy import select

from auth.decorators import jwt_required
from backend.ai import PromptRegistry, ModelRegistry, ModelError
from backend.ai.prompts import ensure_default_prompts


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


def _search_chunks(db, UserFile, Chunk, user_id, query_embedding, *,
                   file_id=None, project_id=None, limit=20, min_score=0.15):
    """Real vector similarity, not keyword fallback — unlike /api/search,
    which also falls back to keyword scoring for chunks with no stored
    embedding. That fallback isn't reproduced here: this endpoint's whole
    point is "vector similarity search against stored embeddings," so a
    chunk without one is skipped rather than scored a different way."""
    file_stmt = select(UserFile).where(UserFile.user_id == user_id, UserFile.kind == "document")
    if file_id is not None:
        file_stmt = file_stmt.where(UserFile.id == file_id)
    if project_id is not None:
        file_stmt = file_stmt.where(UserFile.project_id == project_id)
    file_map = {f.id: f for f in db.execute(file_stmt).scalars().all()}
    if not file_map:
        return []

    chunks = db.execute(
        select(Chunk).where(Chunk.file_id.in_(file_map.keys()))
    ).scalars().all()

    scored = []
    for ch in chunks:
        if not ch.embedding:
            continue
        try:
            emb = json.loads(ch.embedding)
        except (ValueError, TypeError):
            continue
        score = _cosine(query_embedding, emb)
        if score < min_score:
            continue
        scored.append((score, ch, file_map.get(ch.file_id)))

    scored.sort(key=lambda x: -x[0])
    return scored[:limit]


def create_search_blueprint(*, SessionLocal, UserFile, Chunk, utility_model):
    bp = Blueprint("search", __name__)

    @bp.route("/api/documents/search", methods=["GET"])
    @jwt_required()
    def search_documents():
        user_id = int(g.current_user)
        q = (request.args.get("q") or "").strip()
        if len(q) < 2:
            return jsonify({"error": "query_too_short",
                            "message": "Query must be at least 2 characters"}), 400
        file_id = request.args.get("file_id", type=int)
        project_id = request.args.get("project_id", type=int)
        limit = max(1, min(50, request.args.get("limit", default=20, type=int) or 20))

        db = SessionLocal()
        try:
            model_registry = ModelRegistry(db)
            try:
                query_embedding = model_registry.embed(q, user_id=user_id)
            except ModelError as exc:
                return jsonify({"error": "embedding_failed", "message": str(exc)}), 502

            results = _search_chunks(
                db, UserFile, Chunk, user_id, query_embedding,
                file_id=file_id, project_id=project_id, limit=limit,
            )
            return jsonify({"results": [
                {
                    "document_id": ch.file_id,
                    "chunk_id": ch.id,
                    "title": (uf.title or uf.name) if uf else "Document",
                    "file_name": uf.name if uf else None,
                    "snippet": ch.content[:300],
                    "score": round(score, 4),
                    "page": ch.page,
                    "section": ch.section,
                }
                for score, ch, uf in results
            ]})
        finally:
            db.close()

    @bp.route("/api/rag", methods=["POST"])
    @jwt_required()
    def rag_answer():
        user_id = int(g.current_user)
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        if len(query) < 2:
            return jsonify({"error": "query_too_short",
                            "message": "Query must be at least 2 characters"}), 400
        file_id = data.get("file_id")
        project_id = data.get("project_id")
        top_k = max(1, min(20, int(data.get("top_k") or 6)))

        db = SessionLocal()
        try:
            model_registry = ModelRegistry(db)
            try:
                query_embedding = model_registry.embed(query, user_id=user_id)
            except ModelError as exc:
                return jsonify({"error": "embedding_failed", "message": str(exc)}), 502

            results = _search_chunks(
                db, UserFile, Chunk, user_id, query_embedding,
                file_id=file_id, project_id=project_id, limit=top_k,
            )
            if not results:
                return jsonify({
                    "answer": None, "sources": [],
                    "message": "No relevant documents found for this query.",
                }), 200

            documents_text = "\n\n".join(
                f"[{(uf.title or uf.name) if uf else 'document'}]"
                + (f" (p. {ch.page})" if ch.page else "")
                + f"\n{ch.content[:1500]}"
                for _, ch, uf in results
            )

            ensure_default_prompts(db)
            prompt_registry = PromptRegistry(db)
            try:
                prompt = prompt_registry.get_prompt(
                    "semantic_search",
                    variables={"documents": documents_text, "question": query},
                )
                result = model_registry.call(
                    utility_model,
                    [{"role": "user", "content": prompt}],
                    user_id=user_id,
                )
            except ModelError as exc:
                return jsonify({"error": "model_call_failed", "message": str(exc)}), 502

            return jsonify({
                "answer": result["content"],
                "model": result["model"],
                "sources": [
                    {
                        "document_id": ch.file_id,
                        "chunk_id": ch.id,
                        "title": (uf.title or uf.name) if uf else "Document",
                        "score": round(score, 4),
                        "page": ch.page,
                        "section": ch.section,
                    }
                    for score, ch, uf in results
                ],
            }), 200
        finally:
            db.close()

    return bp
