"""SIGN (Scottish Intercollegiate Guidelines Network) framework grader —
the 1++/1+/1-/2++/2+/2-/3/4 scale. Base tier comes from study design
(tier "1" for meta-analyses/systematic reviews/RCTs, tier "2" for
cohort/case-control/observational studies), with the ++/+/- suffix set
by risk_of_bias.overall_risk (LOW/MODERATE/HIGH respectively). Designs
outside SIGN's analytic hierarchy fall back to tier "3" (non-analytic
studies, e.g. case reports/series) with no suffix — the same honest
"insufficient framework fit" fallback used in frameworks/oxford.py.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..enums import GradeType, GradingFramework, RiskLevel
from ..interfaces import BaseFrameworkGrader
from ..models import FrameworkResult, Grade, GradeRationale, PrerequisiteAssessments

_TIER_BY_DESIGN = {
    StudyDesign.SYSTEMATIC_REVIEW: "1",
    StudyDesign.META_ANALYSIS: "1",
    StudyDesign.RCT: "1",
    StudyDesign.COHORT: "2",
    StudyDesign.CASE_CONTROL: "2",
    StudyDesign.OBSERVATIONAL: "2",
}
_FALLBACK_TIER = "3"

_SUFFIX_BY_RISK = {
    RiskLevel.LOW: "++",
    RiskLevel.MODERATE: "+",
    RiskLevel.HIGH: "-",
}

_ASSESSMENT_CONFIDENCE = 0.5


class SIGNGrader(BaseFrameworkGrader):
    """See module docstring."""

    def grade(
        self,
        prerequisites: PrerequisiteAssessments,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> FrameworkResult:
        tier = _TIER_BY_DESIGN.get(classification.study_design.label, _FALLBACK_TIER)
        suffix = _SUFFIX_BY_RISK.get(prerequisites.risk_of_bias.overall_risk, "+") if tier in ("1", "2") else ""
        grade_value = f"{tier}{suffix}"

        rationale = [
            GradeRationale(
                rule_applied="tier_and_risk_suffix",
                evidence_used=list(prerequisites.risk_of_bias.evidence),
                confidence_impact=0.0,
                framework_source=GradingFramework.SIGN.value,
                reasoning=(
                    f"study design {classification.study_design.label.value} -> tier {tier}, "
                    f"risk_of_bias={prerequisites.risk_of_bias.overall_risk.value} -> {grade_value}"
                ),
            )
        ]

        confidence = _ASSESSMENT_CONFIDENCE if prerequisites.risk_of_bias.confidence > 0.0 else 0.3
        evidence = list(prerequisites.risk_of_bias.evidence)

        grade = Grade(
            grade_type=GradeType.EVIDENCE_QUALITY,
            grade_value=grade_value,
            grade_description=f"SIGN level {grade_value}",
            confidence=confidence,
            framework=GradingFramework.SIGN,
            prerequisites_used=self.requires(),
            rationale=rationale,
            evidence=evidence,
        )

        return FrameworkResult(
            framework=GradingFramework.SIGN,
            grade=grade,
            grade_result=None,
            confidence=confidence,
            evidence=evidence,
        )

    def framework(self) -> GradingFramework:
        return GradingFramework.SIGN

    def requires(self) -> list[str]:
        return ["risk_of_bias"]

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 70

    def version(self) -> str:
        return "1.0.0"

    def compatible_frameworks(self) -> list[GradingFramework]:
        return [GradingFramework.GRADE, GradingFramework.OXFORD, GradingFramework.NIH]
