"""Heuristic Research Scope classifier + soft-decline copy.

No LLM. Swap for a model classifier later via the same evaluate_research_scope API.
"""

from __future__ import annotations

import os
import re
from typing import Iterable

from backend.ai.research_scope.types import ScopeDecision, ScopeVerdict

# ── Research-positive cues (scientific programming + lifecycle) ─────────────
_RESEARCH_CUES: tuple[str, ...] = (
    "paper",
    "papers",
    "literature",
    "citation",
    "cite",
    "bibtex",
    "latex",
    "abstract",
    "methodology",
    "hypothesis",
    "experiment",
    "experimental",
    "dataset",
    "data analysis",
    "statistical",
    "statistics",
    "anova",
    "regression",
    "p-value",
    "pvalue",
    "confidence interval",
    "pandas",
    "numpy",
    "scipy",
    "matplotlib",
    "seaborn",
    "jupyter",
    "notebook",
    "reproducib",
    "bioinformat",
    "sequencing",
    "rna-seq",
    "rnaseq",
    "spss",
    "stata",
    "matlab",
    "ggplot",
    "machine learning",
    "deep learning",
    "model training",
    "roc curve",
    "confusion matrix",
    "peer review",
    "systematic review",
    "meta-analysis",
    "prisma",
    "grade",
    "evidence",
    "oa ",
    "open access",
    "doi",
    "pubmed",
    "arxiv",
    "manuscript",
    "thesis",
    "dissertation",
    "figure",
    "plot the",
    "visualize",
    "visualise",
    "csv from",
    "clinical",
    "patient cohort",
    "osteoarthritis",  # common domain example; general domain words also via project
)

# ── Clear off-scope (generic coding / consumer / entertainment) ─────────────
_OFFSCOPE_PHRASES: tuple[str, ...] = (
    "add two numbers",
    "adding 2 numbers",
    "adding two numbers",
    "sum of two",
    "hello world",
    "leetcode",
    "hackerrank",
    "interview question",
    "coding interview",
    "discord bot",
    "minecraft",
    "fortnite",
    "shopping list",
    "write a joke",
    "tell me a joke",
    "horoscope",
    "dating advice",
)

_OFFSCOPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(fizz\s*buzz|palindrome|fibonacci)\b", re.I),
    re.compile(r"\b(todo\s*app|weather\s*app|chat\s*app)\b", re.I),
    re.compile(r"\b(discord|telegram|whatsapp)\s+bot\b", re.I),
    re.compile(r"\b(minecraft|roblox|fortnite)\b", re.I),
)

# Ambiguous “write code” without research cues
_GENERIC_CODE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(write|generate|create|make|give me)\b.{0,40}\b("
        r"python|javascript|typescript|java|c\+\+|csharp|c#|golang|rust|php|ruby|swift|kotlin"
        r")\b",
        re.I,
    ),
    re.compile(r"\b(function|method|class)\b.{0,30}\b(add|sum|multiply|sort|reverse)\b", re.I),
    re.compile(r"\bcode\s+(for|to)\s+(add|sum|sort|reverse|print)\b", re.I),
)


def enforcement_mode() -> str:
    raw = (os.environ.get("RESEARCH_SCOPE_ENFORCEMENT") or "soft_decline").strip().lower()
    if raw in {"0", "false", "no", "off", "disabled"}:
        return "off"
    return "soft_decline"


def _has_any(text: str, cues: Iterable[str]) -> bool:
    return any(c in text for c in cues)


def _decline_copy(*, project_name: str | None) -> str:
    base = (
        "This workspace is optimized for **academic and professional research**, "
        "not general coding assistance or everyday chatbot tasks.\n\n"
        "I can help when the request advances the research lifecycle — for example:\n"
        "- literature discovery and paper understanding\n"
        "- evidence synthesis and academic writing\n"
        "- statistical analysis, experiment scripts, Jupyter / reproducibility\n"
        "- scientific Python/R/MATLAB (pandas, NumPy, plotting, pipelines)\n\n"
        "For general programming homework or consumer apps, a coding assistant "
        "like Cursor or ChatGPT is a better fit."
    )
    if project_name:
        return (
            f"{base}\n\n"
            f"You're in project **{project_name}**. If this was meant for that research "
            f"(analysis, plots, data processing), rephrase with the research goal and I'll help."
        )
    return base


def _clarify_copy(*, project_name: str | None) -> str:
    if project_name:
        return (
            f"Is this for your **{project_name}** research?\n\n"
            "For example I can help with:\n"
            "- statistical analysis or plotting of results\n"
            "- processing experimental datasets\n"
            "- reproducibility / pipeline scripts\n"
            "- methodology or manuscript support\n\n"
            "If yes, tell me the research goal (and data shape if relevant). "
            "If you're looking for general programming help unrelated to research, "
            "a dedicated coding assistant will serve you better."
        )
    return (
        "Dhund is a **Research Operating System**. I can help with scientific "
        "programming when it serves a research goal (analysis, experiments, "
        "reproducibility, visualization).\n\n"
        "What research task is this code for? Or open a project / paper so I can "
        "ground the help in your workspace."
    )


def evaluate_research_scope(
    message: str,
    *,
    project_name: str | None = None,
    paper_scoped: bool = False,
    research_skill: str | None = None,
) -> ScopeDecision:
    """Classify whether a chat prompt belongs in the research lifecycle."""
    if enforcement_mode() == "off":
        return ScopeDecision(verdict=ScopeVerdict.ALLOW, reason_codes=("enforcement_off",))

    text = (message or "").strip()
    if not text:
        return ScopeDecision(verdict=ScopeVerdict.ALLOW, reason_codes=("empty",))

    # Paper / evidence / writing skills are always in-scope product modes
    skill = (research_skill or "").strip().lower()
    if skill and skill not in {"ask", "general", ""}:
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("research_skill", skill),
        )

    if paper_scoped:
        return ScopeDecision(verdict=ScopeVerdict.ALLOW, reason_codes=("paper_scoped",))

    q = text.lower()
    # Project name as soft research cue
    proj = (project_name or "").strip()
    if proj and proj.lower() in q:
        return ScopeDecision(verdict=ScopeVerdict.ALLOW, reason_codes=("project_mentioned",))

    researchy = _has_any(q, _RESEARCH_CUES)

    for phrase in _OFFSCOPE_PHRASES:
        if phrase in q:
            if researchy:
                break
            return ScopeDecision(
                verdict=ScopeVerdict.DECLINE,
                reason_codes=("clear_offscope", phrase.replace(" ", "_")),
                user_message=_decline_copy(project_name=proj or None),
            )

    for pat in _OFFSCOPE_PATTERNS:
        if pat.search(q):
            if researchy:
                break
            return ScopeDecision(
                verdict=ScopeVerdict.DECLINE,
                reason_codes=("offscope_pattern",),
                user_message=_decline_copy(project_name=proj or None),
            )

    if researchy:
        return ScopeDecision(verdict=ScopeVerdict.ALLOW, reason_codes=("research_cues",))

    # Ambiguous generic coding without research cues
    for pat in _GENERIC_CODE_PATTERNS:
        if pat.search(q):
            # Very short toy problems → decline harder
            if re.search(r"\b(two numbers|2 numbers|hello world)\b", q):
                return ScopeDecision(
                    verdict=ScopeVerdict.DECLINE,
                    reason_codes=("generic_coding_toy",),
                    user_message=_decline_copy(project_name=proj or None),
                )
            return ScopeDecision(
                verdict=ScopeVerdict.CLARIFY,
                reason_codes=("ambiguous_coding",),
                user_message=_clarify_copy(project_name=proj or None),
            )

    # Default: allow (don't over-refuse genuine research questions without keywords)
    return ScopeDecision(verdict=ScopeVerdict.ALLOW, reason_codes=("default_allow",))
