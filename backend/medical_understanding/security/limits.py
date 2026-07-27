"""Resource limits — prevents unbounded growth of entities/relations
during extraction from a pathological or adversarial document. Checked
after every registration, not just once at the end, so a runaway
extractor is caught as soon as it crosses the limit rather than after
consuming arbitrarily more memory first.
"""

from ..config import MedicalUnderstandingConfig


class ResourceGuard:
    """See module docstring. Constructed once per pipeline run from the
    active MedicalUnderstandingConfig."""

    def __init__(self, config: MedicalUnderstandingConfig) -> None:
        self.max_entities = config.max_entities
        self.max_relations = config.max_relations
        self.max_evidence = config.max_evidence_references

    def check_limits(self, entity_count: int, relation_count: int) -> bool:
        """True if still within limits, False if either has been
        exceeded — callers stop registering new entities/relations once
        this returns False, rather than raising (a truncated result is
        more useful than a crashed pipeline)."""
        if entity_count > self.max_entities:
            return False
        if relation_count > self.max_relations:
            return False
        return True

    def clamp_evidence(self, evidence: list) -> list:
        """Truncates an evidence list to max_evidence_references —
        applied at output-assembly time, not during extraction, since
        evidence volume is only known once extraction finishes."""
        return evidence[: self.max_evidence]
