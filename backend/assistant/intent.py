"""Intent detection for Assistant Engine — local vs LLM gate."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

IntentKind = Literal[
    "greeting",
    "uncertain",
    "workflow",
    "research_task",
    "writing_task",
    "analysis_task",
    "learning_task",
    "research_question",
    "chat",
]

Mode = Literal["companion", "coach", "teacher", "research_partner", "reviewer"]


@dataclass(frozen=True)
class ClassifiedIntent:
    kind: IntentKind
    label: str
    title: str
    detail: str | None = None
    local_only: bool = False


_GREETING = re.compile(
    r"^(hi|hello|hey|yo|sup|hiya|good\s*(morning|afternoon|evening)|howdy)"
    r"(\s+\w+){0,4}[\s!.]*$",
    re.I,
)
_UNCERTAIN = re.compile(
    r"^(i\s+don'?t\s+know|idk|not\s+sure|unsure|no\s+idea|help\s+me\s+decide|"
    r"what\s+should\s+i\s+do|dunno)[\s.!?]*$",
    re.I,
)
_WORKFLOW = re.compile(
    r"what should i (do|work on)|next step|where (do|should) i start|recommend",
    re.I,
)


def classify_intent(raw: str) -> ClassifiedIntent:
    text = (raw or "").strip()
    lower = text.lower()
    compact = re.sub(r"[^\w\s]", "", lower).strip()

    if _GREETING.match(compact) or compact in {"hi there", "hello there"}:
        return ClassifiedIntent(
            kind="greeting",
            label="Greeting",
            title=text[:40] + ("…" if len(text) > 40 else ""),
            local_only=True,
        )

    if _UNCERTAIN.match(lower) or re.search(
        r"don'?t know what (to do|i('m| am) doing)", lower
    ):
        return ClassifiedIntent(
            kind="uncertain",
            label="Need direction",
            title=text[:48] + ("…" if len(text) > 48 else ""),
            local_only=True,
        )

    if _WORKFLOW.search(lower):
        return ClassifiedIntent(
            kind="workflow",
            label="Workflow",
            title="What should I do next?",
            local_only=True,
        )

    find_m = re.search(
        r"(?:find|search|look\s*up|get)\s+(?:more\s+)?papers?\s+(?:on|about|for)\s+(.+)",
        lower,
    )
    if find_m or re.search(r"find (papers|literature|articles)", lower):
        return ClassifiedIntent(
            kind="research_task",
            label="Research task",
            title="Find papers",
            detail=(find_m.group(1).strip() if find_m else text),
            local_only=False,
        )

    if re.match(r"^(draft|write|revise|rewrite|polish)\b", lower) or (
        re.search(r"\b(introduction|abstract|methods|discussion|conclusion)\b", lower)
        and re.search(r"\b(draft|write|help)\b", lower)
    ):
        return ClassifiedIntent(
            kind="writing_task",
            label="Writing task",
            title=text[:56] + ("…" if len(text) > 56 else ""),
            local_only=False,
        )

    if re.search(r"\b(compare|contrast|contradict|side[- ]by[- ]side)\b", lower) or re.search(
        r"\b(theme|gap|evidence|matrix)\b", lower
    ):
        return ClassifiedIntent(
            kind="analysis_task",
            label="Analysis task",
            title=text[:56] + ("…" if len(text) > 56 else ""),
            local_only=False,
        )

    if re.match(r"^(what is|what's|whats|explain|define|how does|how do|tell me about)\b", lower) or re.search(
        r"\bexplain\b", lower
    ):
        return ClassifiedIntent(
            kind="learning_task",
            label="Learning task",
            title=text[:56] + ("…" if len(text) > 56 else ""),
            local_only=False,
        )

    if text.endswith("?") or re.match(r"^(can|could|should|is|are|does|do|will)\b", lower):
        return ClassifiedIntent(
            kind="research_question",
            label="Research question",
            title=text[:56] + ("…" if len(text) > 56 else ""),
            local_only=False,
        )

    if re.search(r"joke|how are you|thanks|thank you|lol|haha", lower):
        return ClassifiedIntent(
            kind="chat",
            label="Chat",
            title=text[:48] + ("…" if len(text) > 48 else ""),
            local_only=False,
        )

    return ClassifiedIntent(
        kind="research_question",
        label="Research",
        title=text[:56] + ("…" if len(text) > 56 else ""),
        local_only=False,
    )


def select_mode(intent: ClassifiedIntent) -> Mode:
    return {
        "greeting": "companion",
        "uncertain": "coach",
        "workflow": "coach",
        "learning_task": "teacher",
        "writing_task": "reviewer",
        "analysis_task": "research_partner",
        "research_task": "research_partner",
        "research_question": "research_partner",
        "chat": "companion",
    }.get(intent.kind, "research_partner")  # type: ignore[return-value]
