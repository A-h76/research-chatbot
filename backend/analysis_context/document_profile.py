"""Document-level profiling — audience and complexity, layered on top of
classification's already-decided document_type/domain/study_design (read
straight off ClassificationResult, never re-derived — see package
docstring's "Reuse from Classification").

intended_audience and complexity_level are this package's own new
inferences: audience from a small document_type/domain mapping table,
complexity from Phase 1.1's own DocumentStatistics (word/reference
count) — both deterministic, no new text scanning.
"""

from typing import Optional

from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import DocumentStatistics, EvidenceReference, ProcessedDocument

from .enums import AudienceType, ComplexityLevel
from .interfaces import BaseDocumentProfiler
from .models import DocumentProfile

# document_type members with an unambiguous clinical (practitioner-
# facing) audience.
_CLINICAL_DOCUMENT_TYPES = frozenset({DocumentType.CLINICAL_GUIDELINE})

# document_type members whose natural audience is other researchers
# rather than clinicians, even within the medicine domain.
_RESEARCH_DOCUMENT_TYPES = frozenset(
    {
        DocumentType.RESEARCH_ARTICLE,
        DocumentType.SYSTEMATIC_REVIEW,
        DocumentType.META_ANALYSIS,
        DocumentType.CASE_REPORT,
        DocumentType.PROTOCOL,
        DocumentType.THESIS,
    }
)

_TECHNICAL_DOMAINS = frozenset(
    {
        ScientificDomain.COMPUTER_SCIENCE,
        ScientificDomain.AI_ML,
        ScientificDomain.CYBER_SECURITY,
        ScientificDomain.ENGINEERING,
        ScientificDomain.MATHEMATICS,
    }
)

# Complexity thresholds (word count) — deliberately coarse; a precise
# readability model is future work, not attempted here.
_SIMPLE_MAX_WORDS = 1500
_MODERATE_MAX_WORDS = 5000
_COMPLEX_MAX_WORDS = 12000

# A reference list this long bumps complexity up one level regardless of
# prose length — a heavily-cited document is denser to analyze even if
# its own word count looks moderate.
_HIGH_REFERENCE_COUNT = 50

_COMPLEXITY_ORDER = (
    ComplexityLevel.SIMPLE,
    ComplexityLevel.MODERATE,
    ComplexityLevel.COMPLEX,
    ComplexityLevel.VERY_COMPLEX,
)

# Traceability keys (see backend.document_understanding.traceability)
# that evidence the document_type/domain conclusion — only ones with
# real (non-zero-confidence) evidence are included in DocumentProfile.evidence.
_EVIDENCE_KEYS = ("metadata.title", "metadata.venue", "metadata.journal", "metadata.conference")


class DocumentProfiler(BaseDocumentProfiler):
    """Builds a DocumentProfile from a ProcessedDocument's already-
    computed statistics and a ClassificationResult's already-decided
    labels."""

    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> DocumentProfile:
        return DocumentProfile(
            document_type=classification.document_type.label,
            domain=classification.domain.label,
            study_design=classification.study_design.label,
            reporting_guideline=_reporting_guideline(classification),
            intended_audience=_infer_audience(classification.document_type.label, classification.domain.label),
            complexity_level=_infer_complexity(document.statistics),
            confidence=_confidence(classification),
            evidence=_evidence(document),
        )


def _reporting_guideline(classification: ClassificationResult) -> Optional[ReportingGuideline]:
    """None when nothing was detected at all — UNKNOWN isn't itself
    useful information for a downstream consumer the way an actual
    guideline (or ReportingGuideline.NONE, meaning "confidently no
    guideline expected") is."""
    label = classification.reporting_guideline.label
    return None if label == ReportingGuideline.UNKNOWN else label


def _infer_audience(document_type: DocumentType, domain: ScientificDomain) -> AudienceType:
    if domain == ScientificDomain.UNKNOWN:
        return AudienceType.UNKNOWN
    if domain == ScientificDomain.MULTIDISCIPLINARY:
        return AudienceType.MULTIDISCIPLINARY
    if domain == ScientificDomain.MEDICINE:
        if document_type in _CLINICAL_DOCUMENT_TYPES:
            return AudienceType.CLINICAL
        if document_type in _RESEARCH_DOCUMENT_TYPES:
            return AudienceType.RESEARCH
        return AudienceType.CLINICAL
    if domain in _TECHNICAL_DOMAINS:
        return AudienceType.TECHNICAL
    return AudienceType.RESEARCH


def _infer_complexity(statistics: DocumentStatistics) -> ComplexityLevel:
    if statistics.word_count <= 0:
        return ComplexityLevel.UNKNOWN

    if statistics.word_count < _SIMPLE_MAX_WORDS:
        level = ComplexityLevel.SIMPLE
    elif statistics.word_count < _MODERATE_MAX_WORDS:
        level = ComplexityLevel.MODERATE
    elif statistics.word_count < _COMPLEX_MAX_WORDS:
        level = ComplexityLevel.COMPLEX
    else:
        level = ComplexityLevel.VERY_COMPLEX

    if statistics.reference_count >= _HIGH_REFERENCE_COUNT:
        index = _COMPLEXITY_ORDER.index(level)
        level = _COMPLEXITY_ORDER[min(index + 1, len(_COMPLEXITY_ORDER) - 1)]

    return level


def _confidence(classification: ClassificationResult) -> float:
    return (
        classification.document_type.confidence
        + classification.domain.confidence
        + classification.study_design.confidence
    ) / 3


def _evidence(document: ProcessedDocument) -> list[EvidenceReference]:
    return [
        document.traceability[key]
        for key in _EVIDENCE_KEYS
        if key in document.traceability and document.traceability[key].confidence > 0.0
    ]
