"""Builds PICO PromptComponent from MedicalUnderstanding.pico_elements."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding, PICOElements

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType, PromptPriority
from ..interfaces import BasePromptBuilder
from ..models import PromptComponent
from ..security.sanitizers import ContentSanitizer
from ..selectors.strategy_selector import pico_is_complete


class PICOBuilder(BasePromptBuilder):
    """Builds PICO component."""

    def __init__(self, config: Optional[PromptAssemblyConfig] = None) -> None:
        self._config = config or PromptAssemblyConfig()
        self._sanitizer = ContentSanitizer(
            max_length=self._config.max_section_length,
            strip_html_tags=self._config.strip_html,
        )

    def build(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> PromptComponent:
        if not self._config.include_pico or medical.skipped or not pico_is_complete(medical.pico_elements):
            return PromptComponent(
                component_type=PromptComponentType.PICO,
                content="PICO elements not extracted or incomplete.",
                priority=3,
                confidence=0.0,
                evidence=[],
                source="PICOBuilder",
                priority_level=PromptPriority.LOW,
            )

        pico = medical.pico_elements
        assert pico is not None
        content = self._format_pico(pico)
        if self._config.sanitize_user_content:
            content = self._sanitizer.sanitize(content)

        return PromptComponent(
            component_type=PromptComponentType.PICO,
            content=content,
            priority=3,
            confidence=pico.confidence,
            evidence=[],
            source="PICOBuilder",
            priority_level=PromptPriority.HIGH,
        )

    @staticmethod
    def _format_pico(pico: PICOElements) -> str:
        population = pico.population.description if pico.population is not None else "(unknown)"
        interventions = ", ".join(i.name for i in pico.interventions) or "(unknown)"
        comparators = ", ".join(c.name for c in pico.comparators) or "(none reported)"
        outcomes = ", ".join(o.name for o in pico.outcomes) or "(unknown)"
        return (
            f"Population: {population}\n"
            f"Intervention: {interventions}\n"
            f"Comparator: {comparators}\n"
            f"Outcome: {outcomes}"
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 80

    def component_type(self) -> PromptComponentType:
        return PromptComponentType.PICO
