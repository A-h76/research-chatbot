"""Analysis type selection, module requirement mapping, and readiness
scoring — determines which kinds of downstream analysis this document
supports and whether it's actually ready for them, without performing
any of those analyses itself (see package docstring's Non-Goals).

Reuses backend.classification.pass2.keywords.DOCUMENT_TYPE_STRUCTURAL_FEATURES
for readiness scoring (which sections a document_type needs) rather than
building a second table — same reuse section_profile.py already makes.
"""

from backend.classification.pass2.enums import ScientificDomain, StudyDesign
from backend.classification.pass2.keywords import DOCUMENT_TYPE_STRUCTURAL_FEATURES
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .enums import AnalysisType, ReadinessLevel
from .interfaces import BaseAnalysisProfiler
from .models import AnalysisProfile

# Which AnalysisTypes a given StudyDesign supports — a StudyDesign absent
# here contributes nothing beyond the domain-based additions below.
_STUDY_DESIGN_ANALYSIS_TYPES: dict[StudyDesign, tuple[AnalysisType, ...]] = {
    StudyDesign.RCT: (AnalysisType.STATISTICAL_REVIEW, AnalysisType.BIAS_ASSESSMENT, AnalysisType.METHODOLOGY_REVIEW),
    StudyDesign.OBSERVATIONAL: (AnalysisType.STATISTICAL_REVIEW, AnalysisType.BIAS_ASSESSMENT),
    StudyDesign.COHORT: (AnalysisType.STATISTICAL_REVIEW, AnalysisType.BIAS_ASSESSMENT),
    StudyDesign.CASE_CONTROL: (AnalysisType.STATISTICAL_REVIEW, AnalysisType.BIAS_ASSESSMENT),
    StudyDesign.CROSS_SECTIONAL: (AnalysisType.STATISTICAL_REVIEW,),
    StudyDesign.SYSTEMATIC_REVIEW: (
        AnalysisType.EVIDENCE_GRADING,
        AnalysisType.CONSENSUS_DETECTION,
        AnalysisType.GAP_ANALYSIS,
    ),
    StudyDesign.META_ANALYSIS: (
        AnalysisType.EVIDENCE_GRADING,
        AnalysisType.STATISTICAL_REVIEW,
        AnalysisType.CONSENSUS_DETECTION,
    ),
    StudyDesign.DIAGNOSTIC: (AnalysisType.STATISTICAL_REVIEW, AnalysisType.METHODOLOGY_REVIEW),
    StudyDesign.QUALITATIVE: (AnalysisType.METHODOLOGY_REVIEW,),
    StudyDesign.MIXED_METHODS: (AnalysisType.METHODOLOGY_REVIEW, AnalysisType.STATISTICAL_REVIEW),
    StudyDesign.BENCH_EXPERIMENT: (AnalysisType.METHODOLOGY_REVIEW,),
    StudyDesign.ALGORITHM: (AnalysisType.METHODOLOGY_REVIEW, AnalysisType.COMPARATIVE_ANALYSIS),
    StudyDesign.BENCHMARK: (AnalysisType.COMPARATIVE_ANALYSIS, AnalysisType.METHODOLOGY_REVIEW),
    StudyDesign.SYSTEM: (AnalysisType.METHODOLOGY_REVIEW,),
    StudyDesign.FRAMEWORK: (AnalysisType.METHODOLOGY_REVIEW,),
    StudyDesign.DATASET: (AnalysisType.METHODOLOGY_REVIEW,),
    StudyDesign.MODEL: (AnalysisType.COMPARATIVE_ANALYSIS, AnalysisType.METHODOLOGY_REVIEW),
    StudyDesign.SURVEY: (AnalysisType.GAP_ANALYSIS, AnalysisType.KNOWLEDGE_GRAPH),
}

# Additional AnalysisTypes contributed by domain, on top of whatever
# study_design already added.
_DOMAIN_ANALYSIS_TYPES: dict[ScientificDomain, tuple[AnalysisType, ...]] = {
    ScientificDomain.MEDICINE: (AnalysisType.CLINICAL_INTERPRETATION, AnalysisType.DOMAIN_EXTRACTION),
}
_MULTIDISCIPLINARY_ANALYSIS_TYPES = (AnalysisType.KNOWLEDGE_GRAPH, AnalysisType.GAP_ANALYSIS)

# Below this, supported AnalysisTypes are only "suggested" (optional),
# not "required" — never guess a hard module requirement when
# classification itself was uncertain.
_REQUIRED_MODULE_CONFIDENCE_THRESHOLD = 0.5

_FULLY_READY_THRESHOLD = 0.85
_PARTIALLY_READY_THRESHOLD = 0.5
_MINIMALLY_READY_THRESHOLD = 0.2


class AnalysisProfiler(BaseAnalysisProfiler):
    """Builds an AnalysisProfile from a ClassificationResult's already-
    decided labels plus a ProcessedDocument's already-detected structure
    — no new extraction of any kind."""

    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> AnalysisProfile:
        analysis_types = _analysis_types(classification)
        confidence = _confidence(classification)

        module_names = [analysis_type.value for analysis_type in analysis_types]
        if confidence >= _REQUIRED_MODULE_CONFIDENCE_THRESHOLD:
            required_modules, suggested_modules = module_names, []
        else:
            required_modules, suggested_modules = [], module_names

        readiness_score = _readiness_score(document, classification)

        return AnalysisProfile(
            analysis_types=analysis_types,
            required_modules=required_modules,
            suggested_modules=suggested_modules,
            readiness_score=readiness_score,
            readiness_level=_readiness_level(readiness_score, analysis_types),
            limitations=_limitations(document, classification, readiness_score),
            confidence=confidence,
        )


def _analysis_types(classification: ClassificationResult) -> list[AnalysisType]:
    types: list[AnalysisType] = []
    for candidate in _STUDY_DESIGN_ANALYSIS_TYPES.get(classification.study_design.label, ()):
        if candidate not in types:
            types.append(candidate)
    for candidate in _DOMAIN_ANALYSIS_TYPES.get(classification.domain.label, ()):
        if candidate not in types:
            types.append(candidate)
    if classification.domain.label == ScientificDomain.MULTIDISCIPLINARY:
        for candidate in _MULTIDISCIPLINARY_ANALYSIS_TYPES:
            if candidate not in types:
                types.append(candidate)
    return types or [AnalysisType.UNKNOWN]


def _confidence(classification: ClassificationResult) -> float:
    return (classification.study_design.confidence + classification.domain.confidence) / 2


def _readiness_score(document: ProcessedDocument, classification: ClassificationResult) -> float:
    recommended = DOCUMENT_TYPE_STRUCTURAL_FEATURES.get(classification.document_type.label, ())
    if not recommended:
        # No structural expectation for this document type (e.g. an
        # editorial) — readiness is about classification confidence only.
        return classification.document_type.confidence
    present = sum(1 for section_type in recommended if section_type in document.structure.normalized_headings)
    section_ratio = present / len(recommended)
    return (section_ratio + classification.document_type.confidence) / 2


def _readiness_level(readiness_score: float, analysis_types: list[AnalysisType]) -> ReadinessLevel:
    if analysis_types == [AnalysisType.UNKNOWN]:
        return ReadinessLevel.UNKNOWN
    if readiness_score >= _FULLY_READY_THRESHOLD:
        return ReadinessLevel.FULLY_READY
    if readiness_score >= _PARTIALLY_READY_THRESHOLD:
        return ReadinessLevel.PARTIALLY_READY
    if readiness_score >= _MINIMALLY_READY_THRESHOLD:
        return ReadinessLevel.MINIMALLY_READY
    return ReadinessLevel.NOT_READY


def _limitations(
    document: ProcessedDocument, classification: ClassificationResult, readiness_score: float
) -> list[str]:
    limitations: list[str] = []
    recommended = DOCUMENT_TYPE_STRUCTURAL_FEATURES.get(classification.document_type.label, ())
    for section_type in recommended:
        if section_type not in document.structure.normalized_headings:
            limitations.append(f"missing expected section: {section_type.value}")

    if classification.study_design.label == StudyDesign.UNKNOWN:
        limitations.append("study design could not be confidently classified")
    if classification.domain.label == ScientificDomain.UNKNOWN:
        limitations.append("scientific domain could not be confidently classified")
    if readiness_score < _MINIMALLY_READY_THRESHOLD:
        limitations.append("document readiness is too low for reliable downstream analysis")

    return limitations
