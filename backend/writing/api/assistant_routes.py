"""Writing assistant route — Router → Gateway → Model Registry (Bite 3 / 9)."""

from __future__ import annotations

import logging
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
):
    """Factory for ``POST /api/writing``.

    Capability Router → ``invoke_prompt_llm`` → Gateway → Model Registry + AI Ledger.
    """
    bp = Blueprint("writing_assistant_routes", __name__)

    @bp.route("/api/writing", methods=["POST"])
    @login_required
    @limiter.limit("30 per hour")
    def writing_assistant():
        if ai_gateway is None or SessionLocal is None or get_model_registry is None:
            log.error("writing_assistant: gateway not configured")
            return (
                jsonify(
                    {
                        "error": "ai_unavailable",
                        "detail": "Writing assistant is not configured.",
                    }
                ),
                503,
            )

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

        from backend.ai.capability_router.writing_resolve import (
            PROMPT_VERSION_WRITING_ASSISTANT,
            resolve_writing_assistant_execution,
        )
        from backend.ai.utility_engine import invoke_prompt_llm

        plan = resolve_writing_assistant_execution(action=action, quality_mode=quality_mode)
        db = SessionLocal()
        try:
            registry = get_model_registry(db)
            content, provenance = invoke_prompt_llm(
                ai_gateway=ai_gateway,
                model_registry=registry,
                prompt=prompt,
                plan=plan,
                prompt_version=PROMPT_VERSION_WRITING_ASSISTANT,
                path="writing_assistant",
                task="section_generator",
                user_id=uid,
                quality_mode=quality_mode,
                extra={"action": action},
            )
        finally:
            db.close()

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

        payload: dict[str, Any] = {
            "result": content,
            "action": action,
            "warning": warning,
        }
        if provenance:
            payload["ai_execution"] = provenance.get("ai_execution") or provenance
        return jsonify(payload)

    return bp
