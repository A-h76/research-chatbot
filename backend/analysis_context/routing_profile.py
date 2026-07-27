"""Routing decisions — which downstream module pipeline a document
should follow, based purely on already-classified domain/study_design/
document_type (never re-derived, never re-scanning text).

FallbackStrategy (enums.py) exists because RoutingProfile.fallback_strategy
was referenced by the originating task without ever being defined — see
enums.py's own module docstring. Thresholds here mirror
backend.classification.pass2.confidence's "never guess when uncertain"
philosophy, just applied to routing confidence instead of label
selection.
"""

from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .enums import FallbackStrategy, RoutingDecision
from .interfaces import BaseRoutingProfiler
from .models import RoutingProfile

_TECHNICAL_DOMAINS = frozenset(
    {
        ScientificDomain.COMPUTER_SCIENCE,
        ScientificDomain.AI_ML,
        ScientificDomain.CYBER_SECURITY,
        ScientificDomain.MATHEMATICS,
        ScientificDomain.ENGINEERING,
    }
)
_REVIEW_DOCUMENT_TYPES = frozenset({DocumentType.SYSTEMATIC_REVIEW, DocumentType.META_ANALYSIS})
_REVIEW_STUDY_DESIGNS = frozenset({StudyDesign.SYSTEMATIC_REVIEW, StudyDesign.META_ANALYSIS})

# Below this, domain/document_type classification was too uncertain to
# commit to the "full" variant of a routing decision — a scoped/cautious
# variant (or an outright fallback) is used instead.
_HIGH_CONFIDENCE_THRESHOLD = 0.6

# fallback_strategy thresholds, on the same blended confidence used for
# RoutingProfile.confidence.
_MANUAL_REVIEW_THRESHOLD = 0.3
_GENERIC_ANALYSIS_THRESHOLD = 0.5
_SKIP_OPTIONAL_THRESHOLD = 0.7

_MODULE_PIPELINES: dict[RoutingDecision, tuple[str, ...]] = {
    RoutingDecision.CLINICAL_TRIAL: ("medical_understanding", "bias_assessment", "evidence_grading", "prompt_assembly"),
    RoutingDecision.SYSTEMATIC_REVIEW: (
        "medical_understanding",
        "evidence_grading",
        "consensus_detection",
        "prompt_assembly",
    ),
    RoutingDecision.MEDICAL_FULL: ("medical_understanding", "domain_extraction", "prompt_assembly"),
    RoutingDecision.MEDICAL_SCOPED: ("medical_understanding_scoped", "prompt_assembly"),
    RoutingDecision.COMPUTER_SCIENCE: ("technical_understanding", "comparative_analysis", "prompt_assembly"),
    RoutingDecision.MULTIDISCIPLINARY: ("generic_understanding", "knowledge_graph", "prompt_assembly"),
    RoutingDecision.GENERIC: ("generic_understanding", "prompt_assembly"),
    RoutingDecision.UNKNOWN: ("generic_understanding",),
}


class RoutingProfiler(BaseRoutingProfiler):
    """Builds a RoutingProfile purely from ClassificationResult's
    already-decided domain/study_design/document_type labels and their
    own confidences."""

    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> RoutingProfile:
        confidence = _confidence(classification)
        primary = _primary_routing(classification, confidence)
        secondary = _secondary_routing(primary)
        module_pipeline = list(_MODULE_PIPELINES.get(primary, _MODULE_PIPELINES[RoutingDecision.GENERIC]))

        return RoutingProfile(
            primary_routing=primary,
            secondary_routing=secondary,
            module_pipeline=module_pipeline,
            fallback_strategy=_fallback_strategy(confidence),
            priority_weights=_priority_weights(module_pipeline, confidence),
            confidence=confidence,
        )


def _primary_routing(classification: ClassificationResult, confidence: float) -> RoutingDecision:
    domain = classification.domain.label
    document_type = classification.document_type.label
    study_design = classification.study_design.label

    if domain == ScientificDomain.UNKNOWN:
        return RoutingDecision.UNKNOWN

    if domain == ScientificDomain.MEDICINE:
        # Checked before the RCT case below: document_type explicitly
        # classifying this as a review/meta-analysis is a more decisive
        # signal than study_design's own RCT member — see
        # prompt_profile.py's identical precedence choice for why.
        if study_design in _REVIEW_STUDY_DESIGNS or document_type in _REVIEW_DOCUMENT_TYPES:
            return RoutingDecision.SYSTEMATIC_REVIEW
        if study_design == StudyDesign.RCT:
            return RoutingDecision.CLINICAL_TRIAL
        return (
            RoutingDecision.MEDICAL_FULL if confidence >= _HIGH_CONFIDENCE_THRESHOLD else RoutingDecision.MEDICAL_SCOPED
        )

    if domain in _TECHNICAL_DOMAINS:
        return RoutingDecision.COMPUTER_SCIENCE

    if domain == ScientificDomain.MULTIDISCIPLINARY:
        return RoutingDecision.MULTIDISCIPLINARY

    return RoutingDecision.GENERIC


def _secondary_routing(primary: RoutingDecision) -> list[RoutingDecision]:
    if primary in (RoutingDecision.GENERIC, RoutingDecision.UNKNOWN):
        return []
    return [RoutingDecision.GENERIC]


def _fallback_strategy(confidence: float) -> FallbackStrategy:
    if confidence < _MANUAL_REVIEW_THRESHOLD:
        return FallbackStrategy.MANUAL_REVIEW
    if confidence < _GENERIC_ANALYSIS_THRESHOLD:
        return FallbackStrategy.GENERIC_ANALYSIS
    if confidence < _SKIP_OPTIONAL_THRESHOLD:
        return FallbackStrategy.SKIP_OPTIONAL_MODULES
    return FallbackStrategy.NONE


def _priority_weights(module_pipeline: list[str], confidence: float) -> dict[str, float]:
    total = len(module_pipeline)
    return {module: round(confidence * (total - i) / total, 3) for i, module in enumerate(module_pipeline)}


def _confidence(classification: ClassificationResult) -> float:
    return (classification.domain.confidence + classification.document_type.confidence) / 2
