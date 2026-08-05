"""Writing assistant route — Router → Gateway → Model Registry (Bite 3)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable

from flask import Blueprint, jsonify, request, session

log = logging.getLogger(__name__)

WRITING_ACTIONS = {
    "rewrite_academic": (
        "Rewrite the following text in a formal, academic style suitable for "
        "a research paper. Preserve all facts and meaning. "
        "Do not add citations or data that is not already present."
    ),
    "improve_grammar": (
        "Correct all grammar, punctuation, and spelling errors in the text below. "
        "Do not change the meaning or add new content."
    ),
    "improve_clarity": (
        "Rewrite the following text to improve clarity and readability while "
        "keeping the same meaning and academic register."
    ),
    "expand": (
        "Expand the following paragraph with additional explanation and detail. "
        "Stay strictly within what the original text implies — do not invent "
        "facts, citations, or experiments."
    ),
    "shorten": (
        "Shorten the following text, removing redundancy and filler while "
        "preserving the key information."
    ),
    "generate_abstract": (
        "Write a concise academic abstract (150-250 words) for the text below. "
        "Structure: background, objective, method, results, conclusion. "
        "Do not invent data or claims not present in the text."
    ),
    "improve_conclusion": (
        "Rewrite the following conclusion to be stronger, clearer, and more "
        "impactful. Do not add claims not supported by the preceding text."
    ),
}


def create_writing_assistant_blueprint(
    *,
    login_required,
    limiter,
    ai_gateway: Any,
    SessionLocal: Callable[..., Any],
    get_model_registry: Callable[..., Any],
    responses_text: Callable[..., str] | None = None,
):
    """Factory for ``POST /api/writing``.

    Primary path: Capability Router → AI Gateway → Model Registry + AI Ledger.
    ``responses_text`` is retained only as an optional legacy fallback when the
    gateway is not wired (local tests / migration shim).
    """
    bp = Blueprint("writing_assistant_routes", __name__)

    @bp.route("/api/writing", methods=["POST"])
    @login_required
    @limiter.limit("30 per hour")
    def writing_assistant():
        data = request.get_json(silent=True) or {}
        action = str(data.get("action") or "").strip()
        text = str(data.get("text") or "").strip()
        quality_mode = str(data.get("mode") or data.get("quality_mode") or "").strip() or None

        if action not in WRITING_ACTIONS:
            return (
                jsonify(
                    {
                        "error": "invalid_action",
                        "detail": f"Action must be one of: {', '.join(WRITING_ACTIONS)}",
                    }
                ),
                400,
            )

        if not text:
            return (
                jsonify({"error": "text_required", "detail": "text field is required."}),
                400,
            )

        max_chars = 8_000
        warning = ""
        if len(text) > max_chars:
            text = text[:max_chars]
            warning = "Input was truncated to 8 000 characters. For longer texts, split into sections."

        instruction = WRITING_ACTIONS[action]
        prompt = (
            instruction
            + "\n\nIMPORTANT: If you are uncertain or lack context to make a requested "
            "change accurately, say so explicitly rather than inventing content.\n\n"
            + "Text:\n"
            + text
        )

        uid = int(session["user_id"])
        trace_id = str(uuid.uuid4())
        ai_execution: dict[str, Any] | None = None

        if ai_gateway is not None and SessionLocal is not None and get_model_registry is not None:
            from backend.ai.ai_ledger import AILedgerEntry, hash_output, record_execution
            from backend.ai.capability_router.writing_resolve import (
                PROMPT_VERSION_WRITING_ASSISTANT,
                resolve_writing_assistant_execution,
            )

            plan = resolve_writing_assistant_execution(action=action, quality_mode=quality_mode)
            started = time.perf_counter()
            db = SessionLocal()
            try:
                registry = get_model_registry(db)
                result = ai_gateway.call(
                    model_registry=registry,
                    task="section_generator",
                    mode=quality_mode or "balanced",
                    model=plan.model,
                    messages=[{"role": "user", "content": prompt}],
                    user_id=uid,
                )
            finally:
                db.close()
            latency_ms = int((time.perf_counter() - started) * 1000)
            content = (result or {}).get("content") or ""
            if not isinstance(content, str) or not content.strip():
                return (
                    jsonify(
                        {
                            "error": "empty_response",
                            "detail": "Writing assistant returned no content.",
                        }
                    ),
                    502,
                )
            tokens = int((result or {}).get("total_tokens") or 0) or None
            cost = float((result or {}).get("cost") or 0.0)
            tin = (result or {}).get("prompt_tokens")
            tout = (result or {}).get("completion_tokens")
            entry = AILedgerEntry.from_plan(
                plan,
                prompt_version=PROMPT_VERSION_WRITING_ASSISTANT,
                tokens_in=int(tin) if tin is not None else None,
                tokens_out=int(tout) if tout is not None else tokens,
                cost_usd=cost if cost else None,
                latency_ms=latency_ms,
                output_hash=hash_output(content),
                trace_id=trace_id,
                status="completed",
                extra={
                    "user_id": uid,
                    "path": "writing_assistant",
                    "action": action,
                },
            )
            record_execution(entry)
            ai_execution = plan.to_provenance(
                tokens=tokens,
                cost_usd=cost if cost else None,
                duration_ms=latency_ms,
                prompt_version=PROMPT_VERSION_WRITING_ASSISTANT,
                execution_id=entry.execution_id,
            ).to_dict()
            payload: dict[str, Any] = {
                "result": content,
                "action": action,
                "warning": warning,
            }
            if ai_execution:
                payload["ai_execution"] = ai_execution.get("ai_execution") or ai_execution
            return jsonify(payload)

        if responses_text is None:
            log.error("writing_assistant: no gateway and no responses_text fallback")
            return (
                jsonify(
                    {
                        "error": "ai_unavailable",
                        "detail": "Writing assistant is not configured.",
                    }
                ),
                503,
            )

        result = responses_text(prompt)
        return jsonify(
            {
                "result": result,
                "action": action,
                "warning": warning,
            }
        )

    return bp
