"""Research Scope / Prompt Gateway — Research OS identity gate.

Version: 0.1
ADR: docs/adr/0017-research-scope-policy.md
Contract: docs/contracts/research-scope-contract.md

Feature chat must call ``evaluate_research_scope`` before the LLM for
general inquiry. ALLOW continues to Capability Router / model path.
DECLINE / CLARIFY return identity-preserving copy without calling the model.
"""

from __future__ import annotations

from backend.ai.research_scope.evaluate import evaluate_research_scope, enforcement_mode
from backend.ai.research_scope.types import (
    RS_STATUS,
    RS_VERSION,
    ScopeDecision,
    ScopeVerdict,
)

__all__ = [
    "RS_VERSION",
    "RS_STATUS",
    "ScopeVerdict",
    "ScopeDecision",
    "evaluate_research_scope",
    "enforcement_mode",
]
