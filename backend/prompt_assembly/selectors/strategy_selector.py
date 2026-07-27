"""Selects PromptStrategy from profile, PICO completeness, and grades."""

from typing import Optional

from backend.analysis_context.enums import PromptStrategy, RoutingDecision
from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding, PICOElements

from ..config import PromptAssemblyConfig
from ..interfaces import BaseStrategySelector


def pico_is_complete(pico: Optional[PICOElements]) -> bool:
    """PICOElements has no has_pico field — derive from populated arms."""
    if pico is None:
        return False
    has_p = pico.population is not None
    has_i = bool(pico.interventions)
    has_o = bool(pico.outcomes)
    return has_p and has_i and has_o


class StrategySelector(BaseStrategySelector):
    """Selects appropriate prompt strategy."""

    def __init__(self, config: Optional[PromptAssemblyConfig] = None) -> None:
        self._config = config or PromptAssemblyConfig()

    def select(
        self,
        context: AnalysisContext,
        classification: ClassificationResult,
        grades: EvidenceGrades,
        medical: Optional[MedicalUnderstanding] = None,
    ) -> PromptStrategy:
        routing = context.routing_profile.primary_routing

        # Clinical trials / complete PICO → PICO_FIRST
        if routing == RoutingDecision.CLINICAL_TRIAL:
            return PromptStrategy.PICO_FIRST
        if medical is not None and pico_is_complete(medical.pico_elements):
            return PromptStrategy.PICO_FIRST

        # High-quality evidence grades → EVIDENCE_BASED
        if not grades.skipped and grades.confidence.overall >= self._config.high_confidence_threshold:
            return PromptStrategy.EVIDENCE_BASED
        if not grades.skipped and grades.overall_grade.confidence >= self._config.high_confidence_threshold:
            return PromptStrategy.EVIDENCE_BASED

        # Prefer Phase 1.3 profile when set
        if self._config.prefer_context_prompt_profile:
            profile_strategy = context.prompt_profile.prompt_strategy
            if profile_strategy not in (PromptStrategy.CLAIM_BASED,):  # always valid if set
                # SECTION_BASED / HYBRID / SUMMARY_FIRST / DETAILED_FIRST from profile
                if profile_strategy != PromptStrategy.SECTION_BASED or context.prompt_profile.section_priorities:
                    if profile_strategy in (
                        PromptStrategy.SECTION_BASED,
                        PromptStrategy.HYBRID,
                        PromptStrategy.SUMMARY_FIRST,
                        PromptStrategy.DETAILED_FIRST,
                        PromptStrategy.CLAIM_BASED,
                    ):
                        # Still check results completeness for SECTION_BASED confirmation
                        if profile_strategy == PromptStrategy.SECTION_BASED:
                            results_completeness = context.section_profile.section_completeness.get(
                                SectionType.RESULTS, 0.0
                            )
                            if results_completeness > 0.8:
                                return PromptStrategy.SECTION_BASED
                        else:
                            return profile_strategy

        results_completeness = context.section_profile.section_completeness.get(SectionType.RESULTS, 0.0)
        if results_completeness > 0.8:
            return PromptStrategy.SECTION_BASED

        return PromptStrategy.HYBRID

    def supports(self, context: AnalysisContext) -> bool:
        return True
