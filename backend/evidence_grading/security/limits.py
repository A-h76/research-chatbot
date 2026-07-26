"""Resource limits — prevents unbounded growth of outcome grades, bias
domains, rationale strings, and evidence references during grading of a
pathological or adversarial document. Checked at the point each
collection is finalized, not just once at the very end.
"""

from typing import TypeVar

from ..config import EvidenceGradingConfig

_Item = TypeVar("_Item")


class ResourceGuard:
    """See module docstring. Constructed once per pipeline run from the
    active EvidenceGradingConfig."""

    def __init__(self, config: EvidenceGradingConfig) -> None:
        self.max_outcomes = config.max_outcomes
        self.max_bias_domains = config.max_bias_domains
        self.max_rationale_strings = config.max_rationale_strings
        self.max_rationale_length = config.max_rationale_length
        self.max_evidence_references = config.max_evidence_references

    def check_limits(
        self,
        outcome_count: int = 0,
        bias_domain_count: int = 0,
        rationale_count: int = 0,
        evidence_count: int = 0,
    ) -> bool:
        """True if every count is still within its own limit — callers
        stop registering new items once this returns False, rather than
        raising (a truncated result is more useful than a crashed
        pipeline)."""
        if outcome_count > self.max_outcomes:
            return False
        if bias_domain_count > self.max_bias_domains:
            return False
        if rationale_count > self.max_rationale_strings:
            return False
        if evidence_count > self.max_evidence_references:
            return False
        return True

    def clamp_evidence(self, evidence: list[_Item]) -> list[_Item]:
        return evidence[: self.max_evidence_references]

    def clamp_rationale(self, rationale: list[_Item]) -> list[_Item]:
        return rationale[: self.max_rationale_strings]
