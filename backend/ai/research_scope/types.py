"""Research Scope vocabulary — Prompt Gateway (ADR-0017)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

RS_VERSION = "1.0"
RS_STATUS = "frozen_v1"


class ScopeVerdict(str, Enum):
    """Gate outcomes.

    Public product outcomes: ALLOW | CLARIFY | REDIRECT.
    SYSTEM is internal only — auth, uploads, OAuth, billing, jobs must never
    be classified as "research" prompts; callers skip the gate entirely.
    """

    ALLOW = "allow"
    CLARIFY = "clarify"
    REDIRECT = "redirect"
    SYSTEM = "system"  # not user-facing; not emitted by evaluate_research_scope


@dataclass(frozen=True)
class ScopeDecision:
    verdict: ScopeVerdict
    reason_codes: tuple[str, ...] = ()
    user_message: str = ""
    # 0–100 workflow-relevance score (heuristic today; ML classifier later).
    # Measures "does this move research forward?" not merely topical keywords.
    relevance_score: int | None = None
    router_version: str = RS_VERSION

    @property
    def blocks_llm(self) -> bool:
        return self.verdict in (ScopeVerdict.REDIRECT, ScopeVerdict.CLARIFY)

    @property
    def is_user_facing(self) -> bool:
        return self.verdict != ScopeVerdict.SYSTEM

    def to_gate_dict(self) -> dict[str, Any]:
        gate: dict[str, Any] = {
            "verdict": self.verdict.value,
            "reason_codes": list(self.reason_codes),
            "router_version": self.router_version,
        }
        if self.relevance_score is not None:
            gate["relevance_score"] = self.relevance_score
        return {"scope_gate": gate}


def system_scope_decision(*reason_codes: str) -> ScopeDecision:
    """Mark a non-chat platform path that must not enter the research classifier."""
    return ScopeDecision(
        verdict=ScopeVerdict.SYSTEM,
        reason_codes=reason_codes or ("system_path",),
        relevance_score=None,
    )
