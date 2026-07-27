"""Heuristic intent classifier (no LLM). Optional input to PromptRouter."""

from __future__ import annotations

from backend.ai_core.schemas.research_context import ResearchIntent

_KEYWORD_RULES: tuple[tuple[ResearchIntent, tuple[str, ...]], ...] = (
    (ResearchIntent.GAP_ANALYSIS, ("gap", "gaps", "missing", "unanswered", "open question")),
    (ResearchIntent.COMPARE, ("compare", "versus", "vs.", "difference between", "contrast")),
    (ResearchIntent.CRITIQUE, ("critique", "criticise", "criticize", "weakness", "flaw")),
    (ResearchIntent.REVIEW, ("peer review", "critical review", "literature review")),
    (ResearchIntent.OUTLINE, ("outline", "structure a", "section plan")),
    (ResearchIntent.CITATION, ("cite", "citation", "bibtex", "apa", "reference list")),
    (ResearchIntent.WRITING, ("write", "draft", "rewrite", "paragraph", "abstract")),
    (ResearchIntent.READING, ("summarise", "summarize", "summary", "what does the paper")),
    (ResearchIntent.EXPLAIN, ("explain", "what is", "what are", "define")),
)


class IntentClassifier:
    """Map free-text (and optional route hints) → ``ResearchIntent``.

    Keyword heuristics only — swap for a model classifier later via DI.
    """

    def classify(
        self,
        question: str,
        *,
        hint: ResearchIntent | str | None = None,
        **_: object,
    ) -> ResearchIntent:
        if hint is not None:
            return hint if isinstance(hint, ResearchIntent) else ResearchIntent(hint)

        q = (question or "").strip().lower()
        if not q:
            return ResearchIntent.UNKNOWN

        for intent, keywords in _KEYWORD_RULES:
            if any(k in q for k in keywords):
                return intent
        return ResearchIntent.QUESTION
