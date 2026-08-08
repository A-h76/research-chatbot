"""Bridge Assistant Engine decisions into /api/chat (ADR-0018 slice 5).

Keeps a single decision brain for every conversational surface that hits chat.
"""

from __future__ import annotations

from typing import Any


def format_local_reply_text(decision: dict[str, Any]) -> str:
    """Turn a local_reply / ask_profile outcome into assistant message text."""
    lr = decision.get("local_reply") or {}
    lines = [str(x).strip() for x in (lr.get("lines") or []) if str(x).strip()]
    parts = list(lines)

    card = lr.get("action_card")
    if isinstance(card, dict):
        title = (card.get("title") or "").strip()
        actions = card.get("actions") or []
        if title or actions:
            parts.append("")
            if title:
                parts.append(f"**{title}**")
            for a in actions:
                if not isinstance(a, dict):
                    continue
                label = (a.get("label") or "").strip()
                href = (a.get("href") or "").strip()
                if label and href:
                    parts.append(f"- [{label}]({href})")
                elif label:
                    parts.append(f"- {label}")

    questions = lr.get("profile_questions") or []
    for q in questions:
        if not isinstance(q, dict):
            continue
        prompt = (q.get("prompt") or "").strip()
        if prompt:
            parts.append("")
            parts.append(f"**{prompt}**")
        for opt in q.get("options") or []:
            if isinstance(opt, dict) and opt.get("label"):
                parts.append(f"- {opt['label']}")

    return "\n".join(parts).strip()


def should_short_circuit_chat(decision: dict[str, Any] | None) -> bool:
    if not decision:
        return False
    return decision.get("outcome") in {"local_reply", "ask_profile"}


def resolve_chat_assistant_mode(
    decision: dict[str, Any] | None,
    client_mode: str | None,
) -> str | None:
    """Prefer client mode, else Engine mode from start_job / classification."""
    if client_mode:
        return client_mode
    if not decision:
        return None
    start = decision.get("start_job") or {}
    return (start.get("mode") or decision.get("mode") or None)
