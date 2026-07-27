"""Prompt strategy determination — prompt family, section-extraction
order, and evidence-selection scope for downstream prompt assembly
(Phase 1.6). Produces a strategy, not a prompt: no LLM call, no text
generation (see package docstring's Non-Goals).

key_themes reuses ClassificationResult.detected_keywords directly (Phase
1.2's own flat keyword overview) rather than running a second keyword/
theme extraction pass — same "no duplication of classification work"
principle the originating task states for the label fields.

EvidencePriorities.priority_claims is always empty here: identifying
actual textual claims (not just keywords) is claim-level extraction,
explicitly deferred past this phase (see package docstring's Non-Goals
on "Study characteristic extraction beyond what classification
provides") — the field exists on the model now so a later phase
populating it is a field assignment, not a new field.
"""

from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import ProcessedDocument

from .enums import ComplexityLevel, PromptFamily, PromptStrategy
from .interfaces import BasePromptProfiler
from .models import EvidencePriorities, PromptProfile

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
_METHODOLOGICAL_STUDY_DESIGNS = frozenset(
    {StudyDesign.ALGORITHM, StudyDesign.BENCHMARK, StudyDesign.SYSTEM, StudyDesign.FRAMEWORK, StudyDesign.MODEL}
)

# Canonical section-extraction order per document_type — the sections
# most likely to carry the document's key findings first. document_type
# members absent here get the generic fallback order.
_SECTION_PRIORITIES: dict[DocumentType, tuple[SectionType, ...]] = {
    DocumentType.RESEARCH_ARTICLE: (
        SectionType.RESULTS,
        SectionType.METHODS,
        SectionType.DISCUSSION,
        SectionType.ABSTRACT,
    ),
    DocumentType.SYSTEMATIC_REVIEW: (SectionType.RESULTS, SectionType.METHODS, SectionType.DISCUSSION),
    DocumentType.META_ANALYSIS: (SectionType.RESULTS, SectionType.METHODS, SectionType.DISCUSSION),
    DocumentType.CLINICAL_GUIDELINE: (SectionType.DISCUSSION, SectionType.ABSTRACT),
    DocumentType.CASE_REPORT: (SectionType.ABSTRACT, SectionType.DISCUSSION),
    DocumentType.PROTOCOL: (SectionType.METHODS, SectionType.ABSTRACT),
}
_GENERIC_SECTION_PRIORITY = (SectionType.ABSTRACT, SectionType.DISCUSSION)

# How many of ClassificationResult.detected_keywords to surface as
# key_themes — enough to be useful, not the whole (potentially long) list.
_MAX_KEY_THEMES = 10

_DEFAULT_CONFIDENCE_THRESHOLD = 0.5
_DEFAULT_MAX_EVIDENCE_PER_CLAIM = 3

# Thresholds for _prompt_strategy() — a document this long benefits from
# a summary pass before detailed section-by-section extraction; one with
# this many detected sections is structured enough to extract per-section.
_VERY_LONG_WORD_COUNT = 12000
_WELL_STRUCTURED_SECTION_COUNT = 4

# A document classified as a review/meta-analysis is itself a secondary
# synthesis of primary sources — evidence grading built on top of it
# should demand the underlying primary literature, not just the review's
# own summary of it. Primary research (RESEARCH_ARTICLE, RCT, ...) is
# already primary, so nothing further is demanded of it.
_REQUIRES_PRIMARY_SOURCES = _REVIEW_DOCUMENT_TYPES | frozenset({DocumentType.CLINICAL_GUIDELINE})


class PromptProfiler(BasePromptProfiler):
    """Builds a PromptProfile from ClassificationResult's already-decided
    labels and detected_keywords — no new text scanning."""

    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> PromptProfile:
        document_type = classification.document_type.label
        section_priorities = list(_SECTION_PRIORITIES.get(document_type, _GENERIC_SECTION_PRIORITY))

        return PromptProfile(
            prompt_family=_prompt_family(classification),
            prompt_strategy=_prompt_strategy(document, classification),
            section_priorities=section_priorities,
            key_themes=list(classification.detected_keywords[:_MAX_KEY_THEMES]),
            evidence_priorities=EvidencePriorities(
                priority_sections=section_priorities[:3],
                priority_claims=[],
                confidence_threshold=_DEFAULT_CONFIDENCE_THRESHOLD,
                max_evidence_per_claim=_DEFAULT_MAX_EVIDENCE_PER_CLAIM,
                require_primary_sources=document_type in _REQUIRES_PRIMARY_SOURCES,
            ),
            confidence=_confidence(classification),
        )


def _prompt_family(classification: ClassificationResult) -> PromptFamily:
    domain = classification.domain.label
    document_type = classification.document_type.label
    study_design = classification.study_design.label

    if domain == ScientificDomain.UNKNOWN:
        return PromptFamily.UNKNOWN
    if domain == ScientificDomain.MEDICINE:
        # Checked before the RCT case below: document_type explicitly
        # classifying this as a review/meta-analysis is a more decisive
        # signal than study_design's own RCT member — the two would only
        # ever conflict on an inconsistent classification (a genuine
        # systematic-review-of-RCTs paper gets study_design=
        # SYSTEMATIC_REVIEW too, not RCT; see backend.classification.
        # pass2.study_design), and review classification should still win
        # if that ever happens.
        if study_design in (StudyDesign.SYSTEMATIC_REVIEW, StudyDesign.META_ANALYSIS) or document_type in (
            DocumentType.SYSTEMATIC_REVIEW,
            DocumentType.META_ANALYSIS,
        ):
            return PromptFamily.SYSTEMATIC
        if study_design == StudyDesign.RCT:
            return PromptFamily.CLINICAL
        return PromptFamily.MEDICAL
    if study_design in _METHODOLOGICAL_STUDY_DESIGNS:
        return PromptFamily.METHODOLOGICAL
    if domain in _TECHNICAL_DOMAINS:
        return PromptFamily.COMPUTER_SCIENCE
    return PromptFamily.GENERIC


def _prompt_strategy(document: ProcessedDocument, classification: ClassificationResult) -> PromptStrategy:
    word_count = document.statistics.word_count
    section_count = document.statistics.section_count

    if word_count <= 0 or section_count <= 0:
        return PromptStrategy.CLAIM_BASED
    if word_count >= _VERY_LONG_WORD_COUNT:
        return PromptStrategy.SUMMARY_FIRST
    if section_count >= _WELL_STRUCTURED_SECTION_COUNT:
        return PromptStrategy.SECTION_BASED
    if classification.study_design.label == StudyDesign.UNKNOWN and classification.document_type.confidence < 0.5:
        return PromptStrategy.CLAIM_BASED
    return PromptStrategy.HYBRID


def _confidence(classification: ClassificationResult) -> float:
    return (classification.document_type.confidence + classification.domain.confidence) / 2
