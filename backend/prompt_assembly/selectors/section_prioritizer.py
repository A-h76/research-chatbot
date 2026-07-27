"""Prioritizes document sections for inclusion in the assembled prompt."""

from backend.analysis_context.enums import PromptStrategy
from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

_DEFAULT_PRIORITIES = [
    SectionType.ABSTRACT,
    SectionType.INTRODUCTION,
    SectionType.METHODS,
    SectionType.RESULTS,
    SectionType.DISCUSSION,
]

_PICO_FIRST_PRIORITIES = [
    SectionType.METHODS,
    SectionType.RESULTS,
    SectionType.DISCUSSION,
    SectionType.ABSTRACT,
]

_EVIDENCE_FIRST_PRIORITIES = [
    SectionType.RESULTS,
    SectionType.DISCUSSION,
    SectionType.METHODS,
    SectionType.ABSTRACT,
]

_SUMMARY_FIRST_PRIORITIES = [
    SectionType.ABSTRACT,
    SectionType.DISCUSSION,
    SectionType.RESULTS,
]


class SectionPrioritizer:
    """Prioritizes sections based on document type and strategy."""

    def prioritize(
        self,
        context: AnalysisContext,
        classification: ClassificationResult,
        strategy: PromptStrategy,
    ) -> list[SectionType]:
        if strategy == PromptStrategy.PICO_FIRST:
            return list(_PICO_FIRST_PRIORITIES)
        if strategy == PromptStrategy.EVIDENCE_BASED:
            return list(_EVIDENCE_FIRST_PRIORITIES)
        if strategy == PromptStrategy.SUMMARY_FIRST:
            return list(_SUMMARY_FIRST_PRIORITIES)
        if strategy == PromptStrategy.DETAILED_FIRST:
            return list(_DEFAULT_PRIORITIES)

        if strategy == PromptStrategy.SECTION_BASED and context.prompt_profile.section_priorities:
            return list(context.prompt_profile.section_priorities)

        return list(_DEFAULT_PRIORITIES)
