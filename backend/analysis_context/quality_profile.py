"""Input-reliability assessment for the analysis context as a whole.

Not a re-assessment of the document's own quality (that's Phase 1.1's
DocumentQuality, on document.quality) or of classification's own per-
decision confidence (that's already on each ClassificationDecision) —
this blends both into the one signal downstream phases should actually
gate on before trusting the routing/prompt decisions built on top of
them. See models.py's AnalysisQualityProfile docstring for why this
component exists at all: the originating task's own directory tree
names a quality_profile.py file that its Models section never backs
with a class.
"""

from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import QualityLevel
from backend.document_understanding.models import ProcessedDocument

from .models import AnalysisQualityProfile

_LOW_DOCUMENT_QUALITY_THRESHOLD = 0.4
_LOW_CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.4


class QualityProfiler:
    """Builds an AnalysisQualityProfile. No interface (see interfaces.py's
    module docstring): pure arithmetic over already-computed quality/
    confidence data, no plausible second implementation to swap in."""

    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> AnalysisQualityProfile:
        input_document_quality = document.quality.confidence
        input_classification_confidence = _classification_confidence(classification)
        reliability_score = (input_document_quality + input_classification_confidence) / 2

        caveats = list(document.quality.warnings) + list(document.quality.errors)
        if input_document_quality < _LOW_DOCUMENT_QUALITY_THRESHOLD:
            caveats.append("source document quality is low; downstream analysis may be unreliable")
        if input_classification_confidence < _LOW_CLASSIFICATION_CONFIDENCE_THRESHOLD:
            caveats.append("classification confidence is low; routing/prompt decisions may be unreliable")

        return AnalysisQualityProfile(
            input_document_quality=input_document_quality,
            input_classification_confidence=input_classification_confidence,
            reliability_score=reliability_score,
            reliability_level=QualityLevel.from_score(reliability_score),
            caveats=caveats,
        )


def _classification_confidence(classification: ClassificationResult) -> float:
    decisions = (
        classification.document_type,
        classification.domain,
        classification.study_design,
        classification.reporting_guideline,
    )
    return sum(decision.confidence for decision in decisions) / len(decisions)
