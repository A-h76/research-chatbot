"""Writing Planner — decide *what* to write (section slots)."""

from __future__ import annotations

from typing import Any

# Append-only section types for Milestone 1 Research Writing.
SECTION_TYPES = frozenset(
    {
        "support_sentence",
        "introduction",
        "literature_review",
        "discussion",
        "clinical_summary",
        "research_gap",
        "executive_summary",
    }
)

_SECTION_SLOTS: dict[str, list[dict[str, str]]] = {
    "support_sentence": [
        {
            "id": "support",
            "title": "Evidence-backed support",
            "purpose": "Support or refine the selected claim with cited evidence.",
        },
    ],
    "introduction": [
        {
            "id": "problem",
            "title": "Problem framing",
            "purpose": "State the research problem grounded in evidence.",
        },
        {
            "id": "significance",
            "title": "Significance",
            "purpose": "Why the problem matters, citing supporting evidence.",
        },
        {
            "id": "overview",
            "title": "Evidence overview",
            "purpose": "Preview the strongest supporting findings.",
        },
    ],
    "literature_review": [
        {
            "id": "themes",
            "title": "Major themes",
            "purpose": "Synthesize recurring claims across the evidence set.",
        },
        {
            "id": "key_findings",
            "title": "Key findings",
            "purpose": "Highlight high-confidence findings with citations.",
        },
        {
            "id": "tensions",
            "title": "Tensions and limits",
            "purpose": "Note conflicts or gaps already coded in the evidence.",
        },
    ],
    "discussion": [
        {
            "id": "interpretation",
            "title": "Interpretation",
            "purpose": "Interpret supporting evidence relative to the topic.",
        },
        {
            "id": "limitations",
            "title": "Limitations",
            "purpose": "Surface conflict mediators and weak coverage.",
        },
        {
            "id": "implications",
            "title": "Implications",
            "purpose": "State implications strictly implied by the evidence.",
        },
    ],
    "clinical_summary": [
        {
            "id": "population",
            "title": "Population and setting",
            "purpose": "Summarize who/what the evidence covers.",
        },
        {
            "id": "findings",
            "title": "Clinical findings",
            "purpose": "List outcome-relevant claims with citations.",
        },
        {
            "id": "cautions",
            "title": "Cautions",
            "purpose": "Call out conflicts, contested consensus, or thin evidence.",
        },
    ],
    "research_gap": [
        {
            "id": "covered",
            "title": "What is covered",
            "purpose": "Summarize where evidence is present.",
        },
        {
            "id": "undercovered",
            "title": "What is thin or contested",
            "purpose": "Identify contested or conflicted coverage as gaps.",
        },
        {
            "id": "next_questions",
            "title": "Open questions",
            "purpose": "Frame next research questions implied by gaps (no invented facts).",
        },
    ],
    "executive_summary": [
        {
            "id": "headline",
            "title": "Headline finding",
            "purpose": "Lead with the strongest supported claim.",
        },
        {
            "id": "supporting_points",
            "title": "Supporting points",
            "purpose": "Bullet-style synthesis of remaining support.",
        },
        {
            "id": "caveats",
            "title": "Caveats",
            "purpose": "Short caveats from conflict/contested status.",
        },
    ],
}


def normalize_section_type(raw: str | None) -> str:
    value = (raw or "").strip().lower() or "support_sentence"
    if value not in SECTION_TYPES:
        raise ValueError(f"invalid section_type: {value}")
    return value


def plan_sections(
    *,
    section_type: str,
    topic: str = "",
) -> dict[str, Any]:
    """Return an ordered section plan for the Writing stage."""
    st = normalize_section_type(section_type)
    slots = [dict(s) for s in _SECTION_SLOTS[st]]
    return {
        "section_type": st,
        "topic": (topic or "")[:500],
        "slots": slots,
        "slot_count": len(slots),
        "planner_version": "1.0.0",
    }
