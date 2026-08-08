"""Mode-composed prompt layers for Assistant Engine (ADR-0018).

Compose:
  Base personality
  + Researcher profile (from Research State)
  + Project / corpus / journey
  + Mode policy (Teacher | Coach | Reviewer | Partner | Companion)
  + Intent hint

These layers are decision context for the LLM. They do not replace
Capability Router model selection.
"""

from __future__ import annotations

from typing import Any, Mapping

ALLOWED_MODES = frozenset(
    {"companion", "coach", "teacher", "research_partner", "reviewer"}
)

_BASE_PERSONALITY = """=== Dhund Assistant (decision context) ===
You are Dhund — a research operating system assistant, not a generic chatbot.
Dhund has already decided the help mode and research context below.
Rules:
- Do NOT open with a capability list or feature menu.
- Do NOT invent the researcher's project stage, paper counts, or evidence.
- Prefer the Research State below when recommending next steps.
- Answer the user's actual question; teach or coach only when the mode says so.
- Use markdown. Be precise; be honest about uncertainty."""

_MODE_POLICIES: dict[str, str] = {
    "companion": """=== Mode: Companion ===
Tone: warm, brief, human.
Handle greetings and light conversation without pivoting into product pitches.
If research context is relevant, one short grounding sentence is enough — then ask what they want to accomplish.""",
    "coach": """=== Mode: Coach ===
Tone: directive and progress-oriented.
Help the researcher move to the highest-impact next workflow step from Research State.
Prefer a concrete CTA (import papers, extract evidence, review gaps, write) over long essays.
Explain only as much as needed for their experience level.""",
    "teacher": """=== Mode: Teacher ===
Tone: clear explanations, stepwise when the user is a beginner.
Explain concepts accurately; use examples from their field when Research State names one.
Do not assume they know research jargon if experience is beginner.""",
    "research_partner": """=== Mode: Research Partner ===
Tone: peer researcher — concise, technical, grounded.
Answer the research question directly. Cite evidence or note when you lack it.
Skip tutorials unless asked.""",
    "reviewer": """=== Mode: Reviewer ===
Tone: critical, constructive, manuscript-aware.
Critique structure, argument, and evidence use. Do not invent citations.
Prefer actionable revision notes over praise.""",
}


def _as_dict(research_state: Any) -> dict[str, Any]:
    if research_state is None:
        return {}
    if isinstance(research_state, Mapping):
        return dict(research_state)
    to_dict = getattr(research_state, "__dict__", None)
    if callable(getattr(research_state, "to_dict", None)):
        return research_state.to_dict()  # type: ignore[no-any-return]
    # ResearchState dataclass path
    try:
        from backend.assistant.research_state import research_state_to_dict

        return research_state_to_dict(research_state)
    except Exception:
        return {}


def format_research_state_block(research_state: Any) -> str:
    """Deterministic text block — never ask the model to invent these numbers."""
    d = _as_dict(research_state)
    if not d:
        return ""

    user = d.get("user") or {}
    project = d.get("project") or {}
    corpus = d.get("corpus") or {}
    workflow = d.get("workflow") or {}
    writing = d.get("writing") or {}
    next_action = workflow.get("nextAction") or {}

    lines = [
        "=== Research State (computed by Dhund — treat as ground truth) ===",
        f"Experience: {user.get('experience') or 'unknown'}",
    ]
    goals = user.get("goals") or []
    if goals:
        lines.append("Goals: " + ", ".join(str(g) for g in goals))
    fields = user.get("fields") or []
    if fields:
        lines.append("Fields: " + ", ".join(str(f) for f in fields))

    if project.get("title"):
        lines.append(f'Project: "{project.get("title")}" (id={project.get("id")})')
    else:
        lines.append("Project: (none active)")

    lines.append(
        "Corpus: "
        f"papers={corpus.get('papers', 0)}, "
        f"evidence={corpus.get('evidence', 0)}, "
        f"themes={corpus.get('themes', 0)}, "
        f"gaps={corpus.get('gaps', 0)}, "
        f"contradictions={corpus.get('contradictions', 0)}"
        + (
            f", coverage={corpus.get('coverage')}"
            if corpus.get("coverage") is not None
            else ""
        )
    )
    lines.append(
        f"Journey stage: {workflow.get('label') or workflow.get('stage') or 'unknown'}"
    )
    if next_action.get("label"):
        lines.append(
            f"Highest-impact next action: {next_action.get('label')}"
            + (f" → {next_action.get('href')}" if next_action.get("href") else "")
        )
    lines.append(
        "Writing: "
        f"manuscript={'yes' if writing.get('hasManuscript') else 'no'}, "
        f"review_complete={'yes' if writing.get('reviewComplete') else 'no'}"
    )
    blockers = workflow.get("blockers") or []
    if blockers:
        lines.append("Blockers: " + ", ".join(str(b) for b in blockers))
    return "\n".join(lines)


def compose_assistant_layers(
    *,
    mode: str | None,
    research_state: Any = None,
    intent: str | None = None,
) -> str:
    """Return prompt layers to append to chat system instructions."""
    mode_key = (mode or "research_partner").strip().lower()
    if mode_key not in ALLOWED_MODES:
        mode_key = "research_partner"

    parts = [_BASE_PERSONALITY, _MODE_POLICIES[mode_key]]

    state_block = format_research_state_block(research_state)
    if state_block:
        parts.append(state_block)

    if intent:
        parts.append(
            f"=== Current intent (classified by Dhund) ===\nIntent: {intent}"
        )

    experience = ((_as_dict(research_state).get("user") or {}).get("experience") or "").lower()
    if experience == "beginner" and mode_key in {"coach", "teacher"}:
        parts.append(
            "=== Experience adaptation ===\n"
            "User is a beginner: explain jargon briefly; one step at a time; reassure without fluff."
        )
    elif experience in {"advanced", "expert"} and mode_key in {
        "coach",
        "research_partner",
        "reviewer",
    }:
        parts.append(
            "=== Experience adaptation ===\n"
            "User is advanced/expert: be terse; no tutorials; lead with numbers and decisions."
        )

    return "\n\n".join(parts)
