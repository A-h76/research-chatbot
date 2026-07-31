"""Research skills — fixed research operations for chat (W3).

Not an open agent zoo: a small closed set with locked prompt policy +
retrieve knobs. Default skill is ``ask``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ResearchSkillId = Literal["ask", "synthesize", "compare", "extract", "draft"]

SKILL_IDS: tuple[ResearchSkillId, ...] = ("ask", "synthesize", "compare", "extract", "draft")


@dataclass(frozen=True)
class ResearchSkill:
    id: ResearchSkillId
    label: str
    description: str
    top_k: int
    instruction: str


_SKILLS: dict[str, ResearchSkill] = {
    "ask": ResearchSkill(
        id="ask",
        label="Ask",
        description="Answer grounded in scoped sources",
        top_k=6,
        instruction="",
    ),
    "synthesize": ResearchSkill(
        id="synthesize",
        label="Synthesize",
        description="Themes, agreements, and tensions across sources",
        top_k=10,
        instruction=(
            "Research skill: SYNTHESIZE.\n"
            "Organize the answer by themes. For each theme state what the sources "
            "agree on, where they diverge, and what remains unclear. "
            "Cite page/section for each substantive claim. "
            "Do not invent papers or findings outside the excerpts."
        ),
    ),
    "compare": ResearchSkill(
        id="compare",
        label="Compare",
        description="Methods, designs, samples, and outcomes side by side",
        top_k=10,
        instruction=(
            "Research skill: COMPARE.\n"
            "Compare methodology, study design, sample/population, outcomes, and "
            "limitations across the retrieved sources. Prefer a clear structure "
            "(e.g. short table in markdown or parallel bullets). "
            "Cite locators. Flag gaps when a dimension is missing from the excerpts."
        ),
    ),
    "extract": ResearchSkill(
        id="extract",
        label="Extract",
        description="Structured fields (PICO, methods, outcomes)",
        top_k=8,
        instruction=(
            "Research skill: EXTRACT.\n"
            "Extract structured research fields from the excerpts only. "
            "Use this markdown template (omit a row only if truly absent):\n"
            "| Field | Value | Source |\n|---|---|---|\n"
            "| Population / sample | | p. / § |\n"
            "| Intervention / exposure | | |\n"
            "| Comparator | | |\n"
            "| Outcomes / endpoints | | |\n"
            "| Study design | | |\n"
            "| Key methods | | |\n"
            "| Main numerical results | | |\n"
            "| Limitations stated | | |\n"
            "Never invent values — write 'Not in excerpts' when missing."
        ),
    ),
    "draft": ResearchSkill(
        id="draft",
        label="Draft",
        description="Citation-ready paragraph for writing",
        top_k=8,
        instruction=(
            "Research skill: DRAFT.\n"
            "Write a tight academic paragraph (or short section) suitable for a "
            "literature review, grounded only in the excerpts. "
            "Include parenthetical page/section cites. "
            "End with a one-line 'Open questions' note if the excerpts leave gaps. "
            "Do not invent citations."
        ),
    ),
}


def normalize_skill_id(raw: Optional[str]) -> ResearchSkillId:
    key = (raw or "ask").strip().lower()
    if key in _SKILLS:
        return key  # type: ignore[return-value]
    return "ask"


def get_skill(raw: Optional[str]) -> ResearchSkill:
    return _SKILLS[normalize_skill_id(raw)]


def skill_catalog() -> list[dict]:
    return [
        {
            "id": s.id,
            "label": s.label,
            "description": s.description,
        }
        for s in (_SKILLS[i] for i in SKILL_IDS)
    ]
