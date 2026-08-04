"""Heuristic Research Scope classifier + purpose-preserving redirect copy.

Doctrine: Dhund is a workspace with a purpose — every interaction should
either advance research, support the research workflow, or gently redirect
the user back to research (ADR-0017). Not a chatbot with restrictions.

No LLM. Swap for a scored model classifier later via the same
``evaluate_research_scope`` API (relevance_score / workflow-relevance bands).
"""

from __future__ import annotations

import os
import re
from typing import Iterable

from backend.ai.research_scope.types import ScopeDecision, ScopeVerdict

# ── Research-positive cues (lifecycle + workflow support) ───────────────────
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
    "differential gene",
    "gene expression",
    "spss",
    "stata",
    "matlab",
    "ggplot",
    "machine learning",
    "deep learning",
    "model training",
    "roc curve",
    "confusion matrix",
    "kaplan",
    "meier",
    "survival analysis",
    "mixed-effects",
    "mixed effects",
    "peer review",
    "reviewer",
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
    "bayesian",
    "translate",
    "translation",
    "grammar",
    "proofread",
    "copyedit",
    "copy-edit",
    "improve the writing",
    "improve grammar",
    "paraphrase",
    "methods section",
    "results section",
    "discussion section",
    "osteoarthritis",
)

# ── Clear off-scope (entertainment / lifestyle / toy coding) ────────────────
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
    "tell me a story",
    "horoscope",
    "dating advice",
    "birthday poem",
    "write a poem",
    "write me a poem",
    "love poem",
    "plan my vacation",
    "plan a vacation",
    "best pizza",
    "nearby restaurant",
    "what should i cook",
    "write a song",
    "bedtime story",
)

_OFFSCOPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(fizz\s*buzz|palindrome|fibonacci)\b", re.I),
    re.compile(r"\b(todo\s*app|weather\s*app|chat\s*app)\b", re.I),
    re.compile(r"\b(discord|telegram|whatsapp)\s+bot\b", re.I),
    re.compile(r"\b(minecraft|roblox|fortnite)\b", re.I),
    re.compile(r"\b(birthday|wedding|anniversary)\b.{0,20}\b(poem|card|wish|message)\b", re.I),
    re.compile(r"\b(plan|book)\b.{0,20}\b(vacation|holiday|trip|itinerary)\b", re.I),
    re.compile(r"\b(tell|give)\s+me\s+a\s+(joke|riddle|poem|story)\b", re.I),
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

# Score bands (documented in ADR; heuristic assignment today)
_SCORE_ALLOW_STRONG = 92
_SCORE_ALLOW_WORKFLOW = 78
_SCORE_ALLOW_DEFAULT = 72
_SCORE_CLARIFY = 55
_SCORE_REDIRECT = 12


def enforcement_mode() -> str:
    raw = (os.environ.get("RESEARCH_SCOPE_ENFORCEMENT") or "soft_redirect").strip().lower()
    # Accept legacy soft_decline alias.
    if raw in {"0", "false", "no", "off", "disabled"}:
        return "off"
    return "soft_redirect"


def _has_any(text: str, cues: Iterable[str]) -> bool:
    return any(c in text for c in cues)


def _redirect_copy(*, project_name: str | None) -> str:
    """Purpose-preserving redirect with a gentle workflow pivot — not censorship."""
    pivot = (
        "If you're taking a break, I'm still here when you're ready to continue — "
        "literature review, paper analysis, manuscript edits, methods, or evidence checks."
    )
    if project_name:
        return (
            f"This workspace is dedicated to **academic research** "
            f"(project **{project_name}**).\n\n"
            "I'm here to help you advance that work. Your request doesn't appear "
            "related to the research right now. If you're working on a paper, "
            "methodology, analysis, writing, or related tasks, describe that "
            "context and I'll help.\n\n"
            f"{pivot}\n\n"
            "Everyday conversation fits a general AI assistant "
            "(or Dhund's future General AI mode)."
        )
    return (
        "Dhund is designed to help with **research-related work** — literature, "
        "evidence, methods, academic writing, and research analysis code.\n\n"
        "Your request doesn't appear to move a research task forward. "
        "If it does, add the research context and I'll help.\n\n"
        f"{pivot}\n\n"
        "Otherwise, a general AI assistant is the better place for everyday chat."
    )


def _clarify_copy(*, project_name: str | None) -> str:
    if project_name:
        return (
            f"This workspace is dedicated to academic research "
            f"(**{project_name}**).\n\n"
            "I'm here to help you advance that work. Your request isn't clearly "
            "connected yet — if you're writing **research analysis code** or working "
            "on methods / figures / data, tell me the research context and I'll help.\n\n"
            "If this was meant as general programming or casual chat, a general AI "
            "assistant is the better place."
        )
    return (
        "Dhund is a workspace with a purpose: **advancing research**. "
        "I can help with scientific programming when it serves a research goal "
        "(analysis, experiments, reproducibility, visualization).\n\n"
        "What research task is this for? Opening a project or paper also helps me "
        "ground the answer in your workspace."
    )


def evaluate_research_scope(
    message: str,
    *,
    project_name: str | None = None,
    paper_scoped: bool = False,
    research_skill: str | None = None,
) -> ScopeDecision:
    """Classify whether a chat prompt advances or supports research work."""
    if enforcement_mode() == "off":
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("enforcement_off",),
            relevance_score=100,
        )

    text = (message or "").strip()
    if not text:
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("empty",),
            relevance_score=100,
        )

    # Paper / evidence / writing skills are always in-scope product modes
    skill = (research_skill or "").strip().lower()
    if skill and skill not in {"ask", "general", ""}:
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("research_skill", skill),
            relevance_score=_SCORE_ALLOW_STRONG,
        )

    if paper_scoped:
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("paper_scoped",),
            relevance_score=_SCORE_ALLOW_STRONG,
        )

    q = text.lower()
    proj = (project_name or "").strip()
    if proj and proj.lower() in q:
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("project_mentioned",),
            relevance_score=_SCORE_ALLOW_STRONG,
        )

    researchy = _has_any(q, _RESEARCH_CUES)

    for phrase in _OFFSCOPE_PHRASES:
        if phrase in q:
            if researchy:
                break
            return ScopeDecision(
                verdict=ScopeVerdict.REDIRECT,
                reason_codes=("clear_offscope", phrase.replace(" ", "_")),
                user_message=_redirect_copy(project_name=proj or None),
                relevance_score=_SCORE_REDIRECT,
            )

    for pat in _OFFSCOPE_PATTERNS:
        if pat.search(q):
            if researchy:
                break
            return ScopeDecision(
                verdict=ScopeVerdict.REDIRECT,
                reason_codes=("offscope_pattern",),
                user_message=_redirect_copy(project_name=proj or None),
                relevance_score=_SCORE_REDIRECT,
            )

    if researchy:
        return ScopeDecision(
            verdict=ScopeVerdict.ALLOW,
            reason_codes=("research_cues",),
            relevance_score=_SCORE_ALLOW_WORKFLOW,
        )

    # Ambiguous generic coding without research cues
    for pat in _GENERIC_CODE_PATTERNS:
        if pat.search(q):
            if re.search(r"\b(two numbers|2 numbers|hello world)\b", q):
                return ScopeDecision(
                    verdict=ScopeVerdict.REDIRECT,
                    reason_codes=("generic_coding_toy",),
                    user_message=_redirect_copy(project_name=proj or None),
                    relevance_score=_SCORE_REDIRECT,
                )
            return ScopeDecision(
                verdict=ScopeVerdict.CLARIFY,
                reason_codes=("ambiguous_coding",),
                user_message=_clarify_copy(project_name=proj or None),
                relevance_score=_SCORE_CLARIFY,
            )

    # Default: allow genuine research questions that lack keyword hits
    # (e.g. domain-specific methods). Prefer under-redirect over over-refuse.
    return ScopeDecision(
        verdict=ScopeVerdict.ALLOW,
        reason_codes=("default_allow",),
        relevance_score=_SCORE_ALLOW_DEFAULT,
    )
