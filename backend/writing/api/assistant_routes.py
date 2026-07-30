"""Writing assistant route extracted from server.py."""

from __future__ import annotations

from flask import Blueprint, jsonify, request


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
    "shorten": ("Shorten the following text, removing redundancy and filler while " "preserving the key information."),
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


def create_writing_assistant_blueprint(*, login_required, limiter, responses_text):
    bp = Blueprint("writing_assistant_routes", __name__)

    @bp.route("/api/writing", methods=["POST"])
    @login_required
    @limiter.limit("30 per hour")
    def writing_assistant():
        data = request.get_json(silent=True) or {}
        action = str(data.get("action") or "").strip()
        text = str(data.get("text") or "").strip()

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
            warning = "Input was truncated to 8 000 characters. " "For longer texts, split into sections."

        instruction = WRITING_ACTIONS[action]
        prompt = (
            instruction
            + "\n\nIMPORTANT: If you are uncertain or lack context to make a requested "
            "change accurately, say so explicitly rather than inventing content.\n\n"
            + "Text:\n"
            + text
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
