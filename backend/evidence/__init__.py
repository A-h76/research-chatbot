"""Evidence Layer package (Week 2 / Phase 2.2 MVP).

Canonical research-knowledge contract: EvidenceObject.
LLMs may organise and explain; they must never invent evidence.
See docs/architecture/week2-evidence-layer-architecture.md and ADR-0003.
"""

from .scoring import confidence_band_from_grades
from .provenance import compute_content_hash, build_provenance
from .api.errors import EvidenceDomainError, ErrorCode
from .consensus import aggregate_consensus, apply_consensus_stage
from .query import normalize_evidence_query
from .ranking import apply_ranking_stage, rank_evidence_objects

__all__ = [
    "confidence_band_from_grades",
    "compute_content_hash",
    "build_provenance",
    "EvidenceDomainError",
    "ErrorCode",
    "normalize_evidence_query",
    "rank_evidence_objects",
    "apply_ranking_stage",
    "aggregate_consensus",
    "apply_consensus_stage",
]

PIPELINE_VERSION = "2.2.0"
