"""Builds clinical-entities PromptComponent."""

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


class EntitiesBuilder(BasePromptBuilder):
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
        if medical.skipped or not medical.clinical_entities:
            return PromptComponent(
                component_type=PromptComponentType.CLINICAL_ENTITIES,
                content="No clinical entities extracted.",
                priority=5,
                confidence=0.0,
                evidence=[],
                source="EntitiesBuilder",
                priority_level=PromptPriority.LOW,
            )

        threshold = 0.0 if self._config.include_low_confidence_entities else self._config.confidence_threshold
        entities = [e for e in medical.clinical_entities if e.confidence >= threshold]
        entities = entities[: self._config.max_entities]

        lines = []
        for entity in entities:
            label = entity.value or entity.raw_text or "(unnamed)"
            lines.append(f"- {label} ({entity.entity_type.value}, confidence={entity.confidence:.2f})")

        content = "\n".join(lines) if lines else "No clinical entities above confidence threshold."
        if self._config.sanitize_user_content:
            content = self._sanitizer.sanitize(content)

        mean_conf = sum(e.confidence for e in entities) / len(entities) if entities else 0.0
        return PromptComponent(
            component_type=PromptComponentType.CLINICAL_ENTITIES,
            content=content,
            priority=5,
            confidence=mean_conf,
            evidence=[e.evidence for e in entities if e.evidence is not None],
            source="EntitiesBuilder",
            priority_level=PromptPriority.MEDIUM,
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 70

    def component_type(self) -> PromptComponentType:
        return PromptComponentType.CLINICAL_ENTITIES
