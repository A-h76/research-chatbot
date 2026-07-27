"""Selects PromptFamily from routing, classification, and Phase 1.3 profile."""

from backend.analysis_context.enums import PromptFamily, RoutingDecision
from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import DocumentType, ScientificDomain
from backend.classification.pass2.models import ClassificationResult

from ..config import PromptAssemblyConfig
from ..interfaces import BaseTemplateSelector


class FamilySelector:
    """Selects appropriate prompt family based on context."""

    def __init__(self, config: PromptAssemblyConfig | None = None) -> None:
        self._config = config or PromptAssemblyConfig()

    def select(self, context: AnalysisContext, classification: ClassificationResult) -> PromptFamily:
        if self._config.prefer_context_prompt_profile:
            profile_family = context.prompt_profile.prompt_family
            if profile_family not in (PromptFamily.UNKNOWN,):
                # Still allow routing overrides for clinical/systematic —
                # those templates are materially different.
                routing = context.routing_profile.primary_routing
                if routing == RoutingDecision.CLINICAL_TRIAL:
                    return PromptFamily.CLINICAL
                if routing == RoutingDecision.SYSTEMATIC_REVIEW:
                    return PromptFamily.SYSTEMATIC
                return profile_family

        routing = context.routing_profile.primary_routing
        if routing == RoutingDecision.CLINICAL_TRIAL:
            return PromptFamily.CLINICAL
        if routing == RoutingDecision.SYSTEMATIC_REVIEW:
            return PromptFamily.SYSTEMATIC
        if routing == RoutingDecision.MEDICAL_FULL:
            return PromptFamily.MEDICAL
        if routing == RoutingDecision.COMPUTER_SCIENCE:
            return PromptFamily.COMPUTER_SCIENCE

        doc_type = classification.document_type.label
        if doc_type in (
            DocumentType.RESEARCH_ARTICLE,
            DocumentType.CASE_REPORT,
            DocumentType.CLINICAL_GUIDELINE,
            DocumentType.PROTOCOL,
        ):
            if classification.domain.label in (ScientificDomain.MEDICINE, ScientificDomain.BIOLOGY):
                return PromptFamily.MEDICAL
        if doc_type in (DocumentType.SYSTEMATIC_REVIEW, DocumentType.META_ANALYSIS):
            return PromptFamily.SYSTEMATIC
        if classification.domain.label in (ScientificDomain.AI_ML, ScientificDomain.COMPUTER_SCIENCE):
            return PromptFamily.COMPUTER_SCIENCE
        if doc_type in (DocumentType.TECHNICAL_REPORT, DocumentType.WHITE_PAPER):
            return PromptFamily.METHODOLOGICAL

        return self._config.default_prompt_family


class TemplateNameSelector(BaseTemplateSelector):
    """Maps family → template module key."""

    def __init__(self, config: PromptAssemblyConfig | None = None) -> None:
        self._family_selector = FamilySelector(config)

    def select(self, context: AnalysisContext, classification: ClassificationResult) -> str:
        family = self._family_selector.select(context, classification)
        return {
            PromptFamily.MEDICAL: "medical",
            PromptFamily.CLINICAL: "clinical",
            PromptFamily.SYSTEMATIC: "systematic",
            PromptFamily.METHODOLOGICAL: "methodological",
            PromptFamily.COMPUTER_SCIENCE: "cs_ai",
            PromptFamily.GENERIC: "generic",
            PromptFamily.UNKNOWN: "generic",
        }.get(family, "generic")

    def supports(self, context: AnalysisContext) -> bool:
        return True
