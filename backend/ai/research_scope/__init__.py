"""Research Scope / Prompt Gateway — Research OS identity gate.

Version: 1.0 (frozen)
ADR: docs/adr/0017-research-scope-policy.md
Contract: docs/contracts/research-scope-contract.md

Doctrine: Dhund optimizes every interaction for advancing research.

Feature chat calls ``evaluate_research_scope`` before the LLM.
ALLOW continues to Capability Router / model path.
REDIRECT / CLARIFY return purpose-preserving copy without calling the model.
"""

from __future__ import annotations

from backend.ai.research_scope.evaluate import evaluate_research_scope, enforcement_mode
from backend.ai.research_scope.types import (
    RS_STATUS,
    RS_VERSION,
    ScopeDecision,
    ScopeVerdict,
    system_scope_decision,
)

__all__ = [
    "RS_VERSION",
    "RS_STATUS",
    "ScopeVerdict",
    "ScopeDecision",
    "evaluate_research_scope",
    "enforcement_mode",
    "system_scope_decision",
]
