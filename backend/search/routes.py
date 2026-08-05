"""GET /api/documents/search and POST /api/rag — Bearer-JWT-authenticated
counterparts to the session-based POST /api/search (now in
backend/search/semantic_routes.py), same relationship as
/api/documents/upload has to /api/files: an additional flow, not a
replacement (see backend/upload/routes.py's own docstring for the
precedent this follows).

Deliberately does NOT duplicate /api/search's actual search logic or
introduce a second search "engine": both routes here search the exact
same Chunk.embedding data /api/search already uses for its paper results
(real cosine similarity — Chunk stores embeddings as JSON-serialized
floats, no pgvector extension needed, matching how /api/search has
worked all along). SearchIndex (the notes/citations/chat unified index)
is intentionally left untouched — nothing in this codebase has ever
written a row to it; reviving unpopulated schema wasn't asked for and
isn't needed for either route here, which only need paper chunks.

POST /api/rag builds its prompt via PromptBuilder (docs/
prompt-engine-architecture.md §8), not a direct PromptRegistry.get_prompt()
call as it originally did — the first real integration of the Prompt
Engine outside its own package. Picks the model via
ModelRouter.get_model_for_task("rag") rather than a fixed injected
string, and writes one PromptExecution row per call (pending -> success/
failed), closing the audit-trail gap prompt-engine-audit.md flagged.

Phase 2 / F10.4: optional ``limiter`` + ``ai_gate`` (wired from server.py)
prevent unmetered embed/LLM cost. Tests may omit both.

Constructor-injected (SessionLocal, models, get_prompt_builder,
model_router, PromptExecution), never `import server` — same reason as
every other module in auth/, quotas/, and backend/: server.py runs as
__main__, so a module it reaches into importing "server" back
re-executes the whole file under a second module identity and recurses.
"""

import json
import time

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from auth.decorators import jwt_required
from backend.ai import ModelError, ModelRegistry
from backend.ai.prompts import ensure_default_prompts
from backend.ai.utility_engine import invoke_query_embedding
from backend.search.shared import search_user_document_chunks

# Cap query size at the HTTP edge (Phase 2 / F4.1 / F10.4).
MAX_SEARCH_QUERY_CHARS = 2_000
MAX_RAG_QUERY_CHARS = 8_000


def create_search_blueprint(
    *,
    SessionLocal,
    UserFile,
    Chunk,
    get_prompt_builder,
    model_router,
    PromptExecution,
    ai_gateway=None,
    limiter=None,
    ai_gate=None,
):
    bp = Blueprint("search", __name__)

    def _limit(spec):
        def deco(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return deco

    @bp.route("/api/documents/search", methods=["GET"])
    @jwt_required()
    @_limit("30 per minute")
    def search_documents():
        user_id = int(g.current_user)
        q = (request.args.get("q") or "").strip()
        if len(q) < 2:
            return jsonify({"error": "query_too_short", "message": "Query must be at least 2 characters"}), 400
        if len(q) > MAX_SEARCH_QUERY_CHARS:
            return (
                jsonify(
                    {
                        "error": "query_too_long",
                        "message": f"Query must be at most {MAX_SEARCH_QUERY_CHARS} characters",
                    }
                ),
                400,
            )

        if ai_gate is not None:
            from security.ops.gate import AiAccessDenied

            try:
                # Embeddings only — lighter estimate than full RAG completion.
                ai_gate.preflight(user_id, token_estimate=max(50, len(q) // 4), cost_estimate=0.001)
            except AiAccessDenied as exc:
                return jsonify({"error": exc.code, "detail": exc.message}), exc.http_status

        file_id = request.args.get("file_id", type=int)
        project_id = request.args.get("project_id", type=int)
        limit = max(1, min(50, request.args.get("limit", default=20, type=int) or 20))

        db = SessionLocal()
        try:
            model_registry = ModelRegistry(db)
            try:
                query_embedding = invoke_query_embedding(
                    model_registry=model_registry,
                    text=q,
                    user_id=user_id,
                    path="api_documents_search",
                )
            except ModelError as exc:
                return jsonify({"error": "embedding_failed", "message": str(exc)}), 502

            results = search_user_document_chunks(
                db,
                UserFile=UserFile,
                Chunk=Chunk,
                select=select,
                user_id=user_id,
                query_embedding=query_embedding,
                query_text=q,
                file_id=file_id,
                project_id=project_id,
                limit=limit,
                allow_keyword_fallback=False,
            )
            return jsonify(
                {
                    "results": [
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
                    ]
                }
            )
        finally:
            db.close()

    @bp.route("/api/rag", methods=["POST"])
    @jwt_required()
    @_limit("20 per hour")
    def rag_answer():
        user_id = int(g.current_user)
        from security.request_validation import (
            RequestValidationError,
            parse_json_object,
            reject_unknown_fields,
            require_string,
            optional_int,
        )

        try:
            data = parse_json_object(request.get_json(silent=True), allow_empty=False)
            reject_unknown_fields(
                data,
                {
                    "query",
                    "file_id",
                    "project_id",
                    "top_k",
                    "quality_mode",
                    "confidence",
                },
            )
            query = require_string(data, "query", max_len=MAX_RAG_QUERY_CHARS, min_len=2)
        except RequestValidationError as exc:
            return exc.to_response()

        if ai_gate is not None:
            from security.ops.gate import AiAccessDenied

            try:
                ai_gate.preflight(
                    user_id,
                    token_estimate=max(500, len(query) // 3),
                    cost_estimate=0.02,
                )
            except AiAccessDenied as exc:
                return jsonify({"error": exc.code, "detail": exc.message}), exc.http_status

        file_id = data.get("file_id")
        project_id = data.get("project_id")
        top_k = max(1, min(20, int(data.get("top_k") or 6)))

        db = SessionLocal()
        try:
            model_registry = ModelRegistry(db)
            try:
                query_embedding = invoke_query_embedding(
                    model_registry=model_registry,
                    text=query,
                    user_id=user_id,
                    path="api_rag_retrieve",
                )
            except ModelError as exc:
                return jsonify({"error": "embedding_failed", "message": str(exc)}), 502

            results = search_user_document_chunks(
                db,
                UserFile=UserFile,
                Chunk=Chunk,
                select=select,
                user_id=user_id,
                query_embedding=query_embedding,
                query_text=query,
                file_id=file_id,
                project_id=project_id,
                limit=top_k,
                allow_keyword_fallback=False,
            )
            if not results:
                return (
                    jsonify(
                        {
                            "answer": None,
                            "sources": [],
                            "message": "No relevant documents found for this query.",
                        }
                    ),
                    200,
                )

            documents_text = "\n\n".join(
                f"[{(uf.title or uf.name) if uf else 'document'}]"
                + (f" (p. {ch.page})" if ch.page else "")
                + f"\n{ch.content[:1500]}"
                for _, ch, uf in results
            )

            ensure_default_prompts(db)
            builder = get_prompt_builder(db)
            try:
                # rag_context is its own layer, not folded into
                # semantic_search's own {{ documents }} variable — see
                # PromptBuilder's module docstring on why retrieved
                # context always stays a separate section. The model
                # gets `assembled.final` (every non-empty layer, System
                # first), not just the Task layer alone.
                assembled = builder.build(
                    query,
                    "semantic_search",
                    project_id=project_id,
                    user_id=user_id,
                    rag_context=documents_text,
                )
            except ValueError as exc:
                return jsonify({"error": "prompt_assembly_failed", "message": str(exc)}), 502

            quality_mode = (data.get("quality_mode") or "balanced").strip().lower()
            confidence = data.get("confidence")
            if confidence is not None:
                try:
                    confidence = float(confidence)
                except (TypeError, ValueError):
                    confidence = None
            execution = PromptExecution(
                prompt_version_id=assembled.prompt_version_id,
                persona_id=assembled.persona_id,
                project_id=project_id,
                user_id=user_id,
                assembled_prompt=assembled.final,
                status="pending",
            )
            db.add(execution)
            db.commit()

            started = time.perf_counter()
            ai_provenance = None
            try:
                messages = [{"role": "user", "content": assembled.final}]
                source_chunk_ids = [int(ch.id) for _, ch, _ in results if getattr(ch, "id", None)]
                if ai_gateway is not None:
                    from backend.search.search_engine import invoke_rag_llm

                    result, ai_provenance = invoke_rag_llm(
                        ai_gateway=ai_gateway,
                        model_registry=model_registry,
                        messages=messages,
                        user_id=user_id,
                        quality_mode=quality_mode,
                        confidence=confidence,
                        prompt_version_id=assembled.prompt_version_id,
                        project_id=project_id,
                        file_id=file_id,
                        source_chunk_ids=source_chunk_ids,
                    )
                else:
                    from backend.ai.capability_router.search_resolve import resolve_search_execution

                    plan = resolve_search_execution(
                        quality_mode=quality_mode,
                        confidence=confidence,
                    )
                    model = plan.model
                    result = model_registry.call(
                        model,
                        messages,
                        user_id=user_id,
                        prompt_version_id=assembled.prompt_version_id,
                    )
            except ModelError as exc:
                execution.status = "failed"
                db.commit()
                return jsonify({"error": "model_call_failed", "message": str(exc)}), 502

            execution.status = "success"
            execution.tokens_used = result.get("total_tokens")
            execution.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()

            if ai_gate is not None:
                ai_gate.record_usage(
                    user_id,
                    tokens=int(result.get("total_tokens") or 0),
                    cost_usd=float(result.get("cost") or 0.0),
                )

            return (
                jsonify(
                    {
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
                        **(
                            {
                                "ai_execution": (
                                    ai_provenance.get("ai_execution") or ai_provenance
                                )
                            }
                            if ai_provenance
                            else {}
                        ),
                    }
                ),
                200,
            )
        finally:
            db.close()

    return bp
