"""NIH Quality Assessment Tool framework grader — a simplified
GOOD/FAIR/POOR composite, not full 14-item checklist fidelity (the real
NIH tool scores 14 individual items such as research question, eligibility
criteria, blinding, exposure/outcome measurement, statistical adjustment
— reproducing that would require per-item text evidence this pipeline's
own prerequisite assessments don't individually carry). Instead blends
three already-computed signals this pipeline does have: risk of bias,
precision, and reporting quality, each mapped onto a 0-1 scale and
averaged into one composite score, then bucketed into GOOD/FAIR/POOR.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..enums import GradeType, GradingFramework, PrecisionLevel, RiskLevel
from ..interfaces import BaseFrameworkGrader
from ..models import FrameworkResult, Grade, GradeRationale, PrerequisiteAssessments

_RISK_SCORE = {
    RiskLevel.LOW: 1.0,
    RiskLevel.MODERATE: 0.6,
    RiskLevel.HIGH: 0.2,
    RiskLevel.UNCLEAR: 0.4,
    RiskLevel.UNKNOWN: 0.4,
}
_PRECISION_SCORE = {
    PrecisionLevel.HIGH: 1.0,
    PrecisionLevel.MODERATE: 0.6,
    PrecisionLevel.LOW: 0.2,
    PrecisionLevel.UNAVAILABLE: 0.4,
    PrecisionLevel.UNKNOWN: 0.4,
}

_GOOD_THRESHOLD = 0.7
_FAIR_THRESHOLD = 0.4


class NIHGrader(BaseFrameworkGrader):
    """See module docstring."""

    def grade(
        self,
        prerequisites: PrerequisiteAssessments,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> FrameworkResult:
        risk_score = _RISK_SCORE[prerequisites.risk_of_bias.overall_risk]
        precision_score = _PRECISION_SCORE[prerequisites.precision.precision_level]
        reporting_score = prerequisites.reporting_quality.reporting_quality_score / 100.0

        composite = (risk_score + precision_score + reporting_score) / 3
        grade_value = self._bucket(composite)

        rationale = [
            GradeRationale(
                rule_applied="composite_score",
                evidence_used=(
                    list(prerequisites.risk_of_bias.evidence)
                    + list(prerequisites.precision.evidence)
                    + list(prerequisites.reporting_quality.evidence)
                ),
                confidence_impact=0.0,
                framework_source=GradingFramework.NIH.value,
                reasoning=(
                    f"risk_of_bias={risk_score:.2f}, precision={precision_score:.2f}, "
                    f"reporting_quality={reporting_score:.2f} -> composite={composite:.2f} -> {grade_value}"
                ),
            )
        ]

        confidence = (
            prerequisites.risk_of_bias.confidence + prerequisites.precision.confidence + prerequisites.reporting_quality.confidence
        ) / 3
        evidence = (
            list(prerequisites.risk_of_bias.evidence) + list(prerequisites.precision.evidence) + list(prerequisites.reporting_quality.evidence)
        )

        grade = Grade(
            grade_type=GradeType.EVIDENCE_QUALITY,
            grade_value=grade_value,
            grade_description=f"NIH quality rating: {grade_value}",
            confidence=confidence,
            framework=GradingFramework.NIH,
            prerequisites_used=self.requires(),
            rationale=rationale,
            evidence=evidence,
        )

        return FrameworkResult(
            framework=GradingFramework.NIH,
            grade=grade,
            grade_result=None,
            confidence=confidence,
            evidence=evidence,
        )

    def framework(self) -> GradingFramework:
        return GradingFramework.NIH

    def requires(self) -> list[str]:
        return ["risk_of_bias", "precision", "reporting_quality"]

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 80

    def version(self) -> str:
        return "1.0.0"

    def compatible_frameworks(self) -> list[GradingFramework]:
        return [GradingFramework.GRADE, GradingFramework.OXFORD, GradingFramework.SIGN]

    @staticmethod
    def _bucket(composite: float) -> str:
        if composite >= _GOOD_THRESHOLD:
            return "good"
        if composite >= _FAIR_THRESHOLD:
            return "fair"
        return "poor"
