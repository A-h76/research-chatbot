"""Builds evidence-grading PromptComponent from EvidenceGrades."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.enums import GradingFramework
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType, PromptPriority
from ..interfaces import BasePromptBuilder
from ..models import PromptComponent
from ..security.sanitizers import ContentSanitizer


class GradingBuilder(BasePromptBuilder):
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
        if not self._config.include_grading or grades.skipped:
            return PromptComponent(
                component_type=PromptComponentType.GRADING,
                content="Evidence grading not available for this document.",
                priority=4,
                confidence=0.0,
                evidence=[],
                source="GradingBuilder",
                priority_level=PromptPriority.LOW,
            )

        lines = [
            f"Overall grade: {grades.overall_grade.grade_value}",
            f"Study quality: {grades.study_quality.value}",
            f"Risk of bias: {grades.risk_of_bias.overall_risk.value} "
            f"(tool={grades.risk_of_bias.assessment_tool.value})",
            f"Precision: {grades.precision.precision_level.value}",
            f"Directness: {grades.directness.directness_level.value}",
        ]
        if grades.consistency.applicable:
            lines.append(
                f"Consistency: {grades.consistency.consistency_level.value}"
                + (f" (I²={grades.consistency.heterogeneity})" if grades.consistency.heterogeneity is not None else "")
            )

        grade_fw = grades.framework_results.get(GradingFramework.GRADE)
        if grade_fw is not None and grade_fw.grade_result is not None:
            gr = grade_fw.grade_result
            lines.append(f"GRADE quality: {gr.final_quality.value} (initial={gr.initial_quality.value})")
            if gr.recommendation_strength is not None:
                lines.append(f"Recommendation strength: {gr.recommendation_strength.value}")
            if gr.downgrade_factors:
                lines.append("Downgrade factors: " + ", ".join(f.value for f in gr.downgrade_factors))
            if gr.upgrade_factors:
                lines.append("Upgrade factors: " + ", ".join(f.value for f in gr.upgrade_factors))

        content = "\n".join(lines)
        if self._config.sanitize_user_content:
            content = self._sanitizer.sanitize(content)

        return PromptComponent(
            component_type=PromptComponentType.GRADING,
            content=content,
            priority=4,
            confidence=grades.confidence.overall,
            evidence=list(grades.overall_grade.evidence),
            source="GradingBuilder",
            priority_level=PromptPriority.HIGH,
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 75

    def component_type(self) -> PromptComponentType:
        return PromptComponentType.GRADING
