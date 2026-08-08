"""Assistant Engine — decide before generate (ADR-0018)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from backend.assistant.intent import ClassifiedIntent, classify_intent, select_mode
from backend.assistant.research_state import (
    ResearchState,
    is_sparse_experience,
    research_state_to_dict,
)


TODAY_ACTIONS = (
    {
        "id": "continue_lit_review",
        "label": "Continue my literature review",
        "href": "/research/compare",
    },
    {
        "id": "find_papers",
        "label": "Find more papers",
        "href": "/library?upload=1#import",
    },
    {
        "id": "understand_paper",
        "label": "Understand a paper",
        "href": "/library",
    },
    {
        "id": "extract_evidence",
        "label": "Extract evidence",
        "href": "/research/compare?tab=extract",
    },
    {
        "id": "discover_gaps",
        "label": "Discover research gaps",
        "href": "/research/compare?tab=gaps",
    },
    {
        "id": "continue_writing",
        "label": "Continue writing",
        "href": "/writing",
    },
    {
        "id": "ask_question",
        "label": "Ask a research question",
        "focus_composer": True,
    },
)

PROFILE_QUESTIONS = {
    "experience": {
        "id": "experience",
        "prompt": "How experienced are you with research?",
        "options": [
            {"id": "beginner", "label": "Beginner"},
            {"id": "intermediate", "label": "Intermediate"},
            {"id": "advanced", "label": "Advanced"},
        ],
    },
    "focus": {
        "id": "focus",
        "prompt": "What are you working on?",
        "options": [
            {"id": "assignment", "label": "Assignment"},
            {"id": "lit_review", "label": "Literature Review"},
            {"id": "thesis", "label": "Thesis"},
            {"id": "conference", "label": "Conference Paper"},
            {"id": "journal", "label": "Journal Paper"},
        ],
    },
}


def _greeting_hour() -> str:
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


def _first_name(state: ResearchState) -> str:
    name = (state.user.display_name or "").strip()
    if not name:
        return ""
    return name.split()[0]


def _opening_lines(state: ResearchState, *, returning: bool = True) -> list[str]:
    first = _first_name(state)
    sparse = is_sparse_experience(state.user.experience)
    if sparse:
        lines = [f"Welcome back{', ' + first if first else ''}."]
        if state.project.title:
            bits = [
                f"{state.corpus.papers} papers",
                f"{state.corpus.evidence} evidence",
            ]
            if state.corpus.contradictions:
                bits.append(f"{state.corpus.contradictions} contradictions")
            lines.append("Your corpus: " + " · ".join(bits))
        lines.append(f"Next: {state.workflow.next_action.label}.")
        return lines

    lines = [
        f"{_greeting_hour()}{', ' + first if first else ''}.",
    ]
    if returning:
        lines.append("Good to see you again.")
    if state.project.title:
        lines.append(f"You're currently working on {state.project.title}.")
    elif state.user.experience == "beginner":
        lines.append("You're just getting started — I'll guide each step.")
    if state.user.experience == "beginner" and state.corpus.papers == 0:
        lines.append("Today's goal: import papers. I'll explain everything along the way.")
    else:
        lines.append("Before we continue — what are you trying to accomplish today?")
    return lines


def _workflow_lines(state: ResearchState) -> list[str]:
    na = state.workflow.next_action
    sparse = is_sparse_experience(state.user.experience)
    if sparse:
        return [
            (
                f"{state.corpus.papers} papers · {state.corpus.evidence} evidence"
                if state.project.id
                else "No active project yet."
            ),
            f"Next: {na.label}.",
        ]
    lines = []
    if state.project.title:
        lines.append(
            f"Looking at {state.project.title}: "
            f"{state.corpus.papers} papers, {state.corpus.evidence} evidence, "
            f"{state.corpus.themes} themes, {state.corpus.gaps} gaps."
        )
    else:
        lines.append("You don't have an active project yet — start by importing papers.")
    lines.append(f"Highest-impact next step: {na.label}.")
    if na.estimate:
        lines.append(f"Estimated time: {na.estimate}.")
    lines.append("Would you like to start?")
    return lines


def _action_card(state: ResearchState) -> dict[str, Any] | None:
    if is_sparse_experience(state.user.experience):
        na = state.workflow.next_action
        return {
            "title": "Next",
            "actions": [{"id": na.id, "label": na.label, "href": na.href}],
        }
    return {
        "title": "What would you like to do today?",
        "actions": [dict(a) for a in TODAY_ACTIONS],
    }


def _local_reply_for(
    intent: ClassifiedIntent,
    state: ResearchState,
) -> dict[str, Any]:
    if intent.kind == "greeting":
        return {
            "lines": _opening_lines(state, returning=True),
            "action_card": _action_card(state),
        }
    if intent.kind == "uncertain":
        return {
            "lines": [
                "No problem.",
                "Let's figure it out together.",
                "Can I ask two quick questions?",
            ],
            "action_card": None,
            "profile_questions": [
                PROFILE_QUESTIONS["experience"],
                PROFILE_QUESTIONS["focus"],
            ],
        }
    if intent.kind == "workflow":
        return {
            "lines": _workflow_lines(state),
            "action_card": {
                "title": "Recommended",
                "actions": [
                    {
                        "id": state.workflow.next_action.id,
                        "label": state.workflow.next_action.label,
                        "href": state.workflow.next_action.href,
                    }
                ],
            },
        }
    return {
        "lines": _opening_lines(state, returning=True),
        "action_card": _action_card(state),
    }


class AssistantEngine:
    def __init__(self, get_research_state: Callable[..., ResearchState]):
        self._get_state = get_research_state

    def research_state(self, user_id: int, project_id: int | None = None) -> ResearchState:
        return self._get_state(user_id, project_id)

    def open_session(self, user_id: int, project_id: int | None = None) -> dict[str, Any]:
        """Home open — Dhund decides the briefing; no LLM."""
        state = self._get_state(user_id, project_id)
        return {
            "intent": "session_open",
            "mode": "coach" if not is_sparse_experience(state.user.experience) else "companion",
            "research_state": research_state_to_dict(state),
            "outcome": "local_reply",
            "local_reply": {
                "lines": _opening_lines(state, returning=True),
                "action_card": _action_card(state),
            },
        }

    def turn(
        self,
        *,
        user_id: int,
        message: str,
        project_id: int | None = None,
        surface: str = "home",
        conversation_id: int | None = None,
    ) -> dict[str, Any]:
        state = self._get_state(user_id, project_id)
        text = (message or "").strip()
        if not text:
            return self.open_session(user_id, project_id)

        intent = classify_intent(text)
        mode = select_mode(intent)
        base = {
            "intent": intent.kind,
            "intent_meta": {
                "label": intent.label,
                "title": intent.title,
                "detail": intent.detail,
            },
            "mode": mode,
            "research_state": research_state_to_dict(state),
            "surface": surface,
            "conversation_id": conversation_id,
        }

        if intent.local_only:
            return {
                **base,
                "outcome": "ask_profile" if intent.kind == "uncertain" else "local_reply",
                "local_reply": _local_reply_for(intent, state),
            }

        # LLM path — engine decides mode; client/stream uses existing chat.
        return {
            **base,
            "outcome": "start_job",
            "start_job": {
                "kind": "chat",
                "message": text,
                "mode": mode,
                "skill": "ask",
            },
        }


def create_assistant_engine(get_research_state: Callable[..., ResearchState]) -> AssistantEngine:
    return AssistantEngine(get_research_state)
