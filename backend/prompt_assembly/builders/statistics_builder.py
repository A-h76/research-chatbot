"""Builds statistics PromptComponent from MedicalUnderstanding."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType, PromptPriority
from ..interfaces import BasePromptBuilder
from ..models import PromptComponent
from ..security.sanitizers import ContentSanitizer


class StatisticsBuilder(BasePromptBuilder):
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
        if not self._config.include_statistics or medical.skipped or not medical.statistical_measures:
            return PromptComponent(
                component_type=PromptComponentType.STATISTICS,
                content="No statistical measures extracted.",
                priority=6,
                confidence=0.0,
                evidence=[],
                source="StatisticsBuilder",
                priority_level=PromptPriority.LOW,
            )

        measures = [
            m
            for m in medical.statistical_measures
            if m.confidence >= self._config.confidence_threshold
        ][: self._config.max_entities]

        lines = []
        for measure in measures:
            outcome = f" ({measure.associated_outcome})" if measure.associated_outcome else ""
            lines.append(f"- {measure.measure_type.value}: {measure.value}{outcome}")

        content = "\n".join(lines) if lines else "No statistical measures above confidence threshold."
        if self._config.sanitize_user_content:
            content = self._sanitizer.sanitize(content)

        mean_conf = sum(m.confidence for m in measures) / len(measures) if measures else 0.0
        return PromptComponent(
            component_type=PromptComponentType.STATISTICS,
            content=content,
            priority=6,
            confidence=mean_conf,
            evidence=[m.evidence for m in measures if m.evidence is not None],
            source="StatisticsBuilder",
            priority_level=PromptPriority.MEDIUM,
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 60

    def component_type(self) -> PromptComponentType:
        return PromptComponentType.STATISTICS
