"""Deterministic Research State + journey derivation (ADR-0018).

Stages and next actions are pure functions of system signals — never LLM guesses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Journey stages (product Research State — not Bite 15 per-file workflow steps)
STAGE_DISCOVERY = "discovery"
STAGE_LIBRARY = "library"
STAGE_EVIDENCE = "evidence_extraction"
STAGE_SYNTHESIS = "synthesis"
STAGE_WRITING = "writing"
STAGE_REVIEW = "review"
STAGE_PUBLISH = "publish"

JOURNEY_ORDER = (
    STAGE_DISCOVERY,
    STAGE_LIBRARY,
    STAGE_EVIDENCE,
    STAGE_SYNTHESIS,
    STAGE_WRITING,
    STAGE_REVIEW,
    STAGE_PUBLISH,
)

STAGE_LABELS = {
    STAGE_DISCOVERY: "Question",
    STAGE_LIBRARY: "Library",
    STAGE_EVIDENCE: "Evidence",
    STAGE_SYNTHESIS: "Synthesis",
    STAGE_WRITING: "Writing",
    STAGE_REVIEW: "Review",
    STAGE_PUBLISH: "Publish",
}


@dataclass(frozen=True)
class NextAction:
    id: str
    label: str
    href: str
    estimate: str | None = None


@dataclass(frozen=True)
class CorpusSignals:
    papers: int = 0
    evidence: int = 0
    themes: int = 0
    gaps: int = 0
    contradictions: int = 0
    coverage: float | None = None
    unread: int = 0


@dataclass(frozen=True)
class WritingSignals:
    has_manuscript: bool = False
    citation_count: int = 0
    review_complete: bool = False


@dataclass(frozen=True)
class UserSignals:
    experience: str = "intermediate"
    goals: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    role: str | None = None
    display_name: str = ""


@dataclass(frozen=True)
class ProjectSignals:
    id: int | None = None
    title: str | None = None
    discipline: str | None = None


@dataclass(frozen=True)
class JourneyState:
    stage: str
    label: str
    completion: dict[str, int]
    next_action: NextAction
    blockers: tuple[str, ...] = ()
    stages: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ResearchState:
    user: UserSignals
    project: ProjectSignals
    corpus: CorpusSignals
    writing: WritingSignals
    workflow: JourneyState


def _experience(raw: str | None) -> str:
    v = (raw or "").strip().lower()
    if v in {"beginner", "intermediate", "advanced", "expert"}:
        return v
    return "intermediate"


def is_sparse_experience(experience: str) -> bool:
    return experience in {"advanced", "expert"}


def derive_stage(corpus: CorpusSignals, writing: WritingSignals, has_project: bool) -> str:
    """Pure stage from signals. Order matters — first match wins."""
    if not has_project:
        return STAGE_DISCOVERY
    if corpus.papers <= 0:
        return STAGE_LIBRARY
    if corpus.evidence <= 0:
        return STAGE_EVIDENCE
    if writing.has_manuscript and writing.review_complete:
        return STAGE_PUBLISH
    if writing.has_manuscript:
        return STAGE_WRITING
    # Evidence present, not yet writing — synthesis (themes/gaps/compare)
    return STAGE_SYNTHESIS


def derive_next_action(
    corpus: CorpusSignals,
    writing: WritingSignals,
    *,
    has_project: bool,
) -> NextAction:
    if not has_project or corpus.papers <= 0:
        return NextAction(
            id="import_papers",
            label="Import papers",
            href="/library?upload=1#import",
            estimate="A few minutes",
        )
    if corpus.evidence <= 0:
        return NextAction(
            id="extract_evidence",
            label="Extract evidence",
            href="/research/compare?tab=extract",
            estimate="About 3 minutes",
        )
    if corpus.gaps > 0:
        return NextAction(
            id="review_gaps",
            label="Review research gaps",
            href="/research/compare?tab=gaps",
            estimate="5–10 minutes",
        )
    if corpus.contradictions > 0:
        return NextAction(
            id="inspect_contradictions",
            label="Inspect contradictions",
            href="/research/compare?tab=graph",
        )
    if not writing.has_manuscript:
        return NextAction(
            id="start_writing",
            label="Start writing",
            href="/writing",
        )
    if corpus.unread > 0:
        return NextAction(
            id="unread_papers",
            label="Catch up on unread papers",
            href="/library?reading_status=unread",
        )
    return NextAction(
        id="compare_papers",
        label="Compare papers",
        href="/research/compare?tab=compare",
    )


def _journey_checklist(corpus: CorpusSignals, writing: WritingSignals, has_project: bool) -> tuple[dict[str, Any], ...]:
    """Seven-stage journey for UI (done / in_progress / locked)."""
    stage = derive_stage(corpus, writing, has_project)
    idx = JOURNEY_ORDER.index(stage) if stage in JOURNEY_ORDER else 0
    out: list[dict[str, Any]] = []
    checks = {
        STAGE_DISCOVERY: has_project or bool(corpus.papers),
        STAGE_LIBRARY: corpus.papers > 0,
        STAGE_EVIDENCE: corpus.evidence > 0,
        STAGE_SYNTHESIS: corpus.themes > 0 or corpus.gaps > 0 or corpus.evidence > 0,
        STAGE_WRITING: writing.has_manuscript,
        STAGE_REVIEW: writing.review_complete,
        STAGE_PUBLISH: writing.review_complete,
    }
    for i, sid in enumerate(JOURNEY_ORDER):
        if checks.get(sid):
            status = "done"
        elif i == idx:
            status = "in_progress"
        else:
            status = "locked"
        out.append({"id": sid, "label": STAGE_LABELS[sid], "status": status})
    return tuple(out)


def derive_completion(corpus: CorpusSignals, writing: WritingSignals, has_project: bool) -> dict[str, int]:
    stages = _journey_checklist(corpus, writing, has_project)
    done = sum(1 for s in stages if s["status"] == "done")
    return {"done": done, "total": len(JOURNEY_ORDER)}


def derive_blockers(corpus: CorpusSignals, writing: WritingSignals, has_project: bool) -> tuple[str, ...]:
    blockers: list[str] = []
    if not has_project:
        blockers.append("no_active_project")
    elif corpus.papers <= 0:
        blockers.append("no_papers")
    elif corpus.evidence <= 0:
        blockers.append("no_evidence")
    return tuple(blockers)


def derive_journey(
    corpus: CorpusSignals,
    writing: WritingSignals,
    *,
    has_project: bool,
) -> JourneyState:
    stage = derive_stage(corpus, writing, has_project)
    return JourneyState(
        stage=stage,
        label=STAGE_LABELS.get(stage, stage),
        completion=derive_completion(corpus, writing, has_project),
        next_action=derive_next_action(corpus, writing, has_project=has_project),
        blockers=derive_blockers(corpus, writing, has_project),
        stages=_journey_checklist(corpus, writing, has_project),
    )


def build_research_state(
    *,
    user: UserSignals,
    project: ProjectSignals,
    corpus: CorpusSignals,
    writing: WritingSignals,
) -> ResearchState:
    journey = derive_journey(corpus, writing, has_project=project.id is not None)
    return ResearchState(
        user=user,
        project=project,
        corpus=corpus,
        writing=writing,
        workflow=journey,
    )


def user_signals_from_orm(user: Any) -> UserSignals:
    fields_raw = getattr(user, "research_fields", None) or ""
    fields = tuple(f.strip() for f in str(fields_raw).split(",") if f.strip())
    goal = (getattr(user, "research_goal", None) or "").strip()
    goals = (goal,) if goal else ()
    return UserSignals(
        experience=_experience(getattr(user, "experience_level", None)),
        goals=goals,
        fields=fields,
        role=getattr(user, "research_role", None) or None,
        display_name=(getattr(user, "name", None) or "").strip(),
    )


def research_state_to_dict(state: ResearchState) -> dict[str, Any]:
    na = state.workflow.next_action
    return {
        "user": {
            "experience": state.user.experience,
            "goals": list(state.user.goals),
            "fields": list(state.user.fields),
            "role": state.user.role,
            "display_name": state.user.display_name,
        },
        "project": {
            "id": state.project.id,
            "title": state.project.title,
            "discipline": state.project.discipline,
        },
        "corpus": {
            "papers": state.corpus.papers,
            "evidence": state.corpus.evidence,
            "themes": state.corpus.themes,
            "gaps": state.corpus.gaps,
            "contradictions": state.corpus.contradictions,
            "coverage": state.corpus.coverage,
            "unread": state.corpus.unread,
        },
        "workflow": {
            "stage": state.workflow.stage,
            "label": state.workflow.label,
            "completion": dict(state.workflow.completion),
            "nextAction": {
                "id": na.id,
                "label": na.label,
                "href": na.href,
                "estimate": na.estimate,
            },
            "blockers": list(state.workflow.blockers),
            "stages": [dict(s) for s in state.workflow.stages],
        },
        "writing": {
            "hasManuscript": state.writing.has_manuscript,
            "citationCount": state.writing.citation_count,
            "reviewComplete": state.writing.review_complete,
        },
    }
