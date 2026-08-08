"""Tests for Assistant Engine ↔ chat bridge (ADR-0018 slice 5)."""

from backend.assistant.chat_bridge import (
    format_local_reply_text,
    resolve_chat_assistant_mode,
    should_short_circuit_chat,
)


def test_format_local_reply_with_actions():
    text = format_local_reply_text(
        {
            "outcome": "local_reply",
            "local_reply": {
                "lines": ["Good evening.", "What are you working on today?"],
                "action_card": {
                    "title": "What would you like to do today?",
                    "actions": [
                        {
                            "id": "extract_evidence",
                            "label": "Extract evidence",
                            "href": "/research/compare?tab=extract",
                        }
                    ],
                },
            },
        }
    )
    assert "Good evening." in text
    assert "**What would you like to do today?**" in text
    assert "[Extract evidence](/research/compare?tab=extract)" in text


def test_short_circuit_outcomes():
    assert should_short_circuit_chat({"outcome": "local_reply"})
    assert should_short_circuit_chat({"outcome": "ask_profile"})
    assert not should_short_circuit_chat({"outcome": "start_job"})
    assert not should_short_circuit_chat(None)


def test_resolve_mode_prefers_client():
    assert (
        resolve_chat_assistant_mode({"mode": "teacher"}, "reviewer") == "reviewer"
    )
    assert (
        resolve_chat_assistant_mode(
            {"mode": "coach", "start_job": {"mode": "teacher"}}, None
        )
        == "teacher"
    )
