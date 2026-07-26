"""Builds evidence PromptComponent from EvidenceGrades (and medical findings)."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import EvidenceReference, ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType, PromptPriority
from ..interfaces import BasePromptBuilder
from ..models import PromptComponent
from ..security.sanitizers import ContentSanitizer


class EvidenceBuilder(BasePromptBuilder):
    """Builds evidence component with confidence filtering."""

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
        if grades.skipped:
            return PromptComponent(
                component_type=PromptComponentType.EVIDENCE,
                content="Evidence grading was not required for this document; no graded evidence summary available.",
                priority=2,
                confidence=0.0,
                evidence=[],
                source="EvidenceBuilder",
                priority_level=PromptPriority.LOW,
            )

        refs = self._collect_evidence(grades, medical)
        threshold = self._config.evidence_threshold if self._config.include_evidence_with_confidence else 0.0
        filtered = [r for r in refs if r.confidence >= threshold][: self._config.max_evidence_per_claim * 5]

        lines = [
            f"Overall grade: {grades.overall_grade.grade_value} "
            f"({grades.overall_grade.grade_description or 'n/a'})",
            f"Study quality: {grades.study_quality.value}",
            f"Risk of bias: {grades.risk_of_bias.overall_risk.value}",
        ]
        if filtered:
            lines.append("Evidence snippets:")
            for ref in filtered[: self._config.max_evidence_per_claim * 3]:
                snippet = (ref.text_snippet or "")[:200]
                if self._config.sanitize_user_content:
                    snippet = self._sanitizer.sanitize(snippet)
                page = f"p.{ref.page}" if ref.page is not None else "p.?"
                lines.append(f"- [{page}] {snippet}")

        content = "\n".join(lines)
        if self._config.sanitize_user_content:
            content = self._sanitizer.sanitize(content)

        return PromptComponent(
            component_type=PromptComponentType.EVIDENCE,
            content=content,
            priority=2,
            confidence=grades.confidence.overall,
            evidence=filtered,
            source="EvidenceBuilder",
            priority_level=PromptPriority.HIGH,
        )

    @staticmethod
    def _collect_evidence(grades: EvidenceGrades, medical: MedicalUnderstanding) -> list[EvidenceReference]:
        """EvidenceGrades has no evidence_references field — collect from
        grade + assessments + medical key findings."""
        refs: list[EvidenceReference] = []
        refs.extend(grades.overall_grade.evidence)
        refs.extend(grades.risk_of_bias.evidence)
        refs.extend(grades.precision.evidence)
        refs.extend(grades.directness.evidence)
        if grades.consistency.applicable:
            refs.extend(grades.consistency.evidence)
        if grades.publication_bias is not None and grades.publication_bias.applicable:
            refs.extend(grades.publication_bias.evidence)
        for finding in medical.key_findings:
            if finding.evidence is not None:
                refs.append(finding.evidence)
        return refs

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 90

    def component_type(self) -> PromptComponentType:
        return PromptComponentType.EVIDENCE
