"""Evidence Layer package (Week 2 / Phase 2.2 MVP).

Canonical research-knowledge contract: EvidenceObject.
LLMs may organise and explain; they must never invent evidence.
See docs/architecture/week2-evidence-layer-architecture.md and ADR-0003.
"""

from .scoring import confidence_band_from_grades
from .provenance import compute_content_hash, build_provenance
from .api.errors import EvidenceDomainError, ErrorCode

__all__ = [
    "confidence_band_from_grades",
    "compute_content_hash",
    "build_provenance",
    "EvidenceDomainError",
    "ErrorCode",
]

PIPELINE_VERSION = "2.2.0"
