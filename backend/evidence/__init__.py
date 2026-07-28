"""Evidence Layer package (Week 2 / Phase 2.2 MVP).

Canonical research-knowledge contract: EvidenceObject.
LLMs may organise and explain; they must never invent evidence.
See docs/architecture/week2-evidence-layer-architecture.md and ADR-0003.
"""

from .scoring import confidence_band_from_grades
from .provenance import compute_content_hash, build_provenance
from .api.errors import EvidenceDomainError, ErrorCode
from .conflict import analyze_conflicts, apply_conflict_stage
from .consensus import aggregate_consensus, apply_consensus_stage
from .query import normalize_evidence_query
from .ranking import apply_ranking_stage, rank_evidence_objects
from .reasoning import apply_reasoning_stage, build_reasoning
from .writing_intelligence import apply_writing_intelligence_stage, build_writing_intelligence

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
    "analyze_conflicts",
    "apply_conflict_stage",
    "build_reasoning",
    "apply_reasoning_stage",
    "build_writing_intelligence",
    "apply_writing_intelligence_stage",
]

PIPELINE_VERSION = "2.2.0"
