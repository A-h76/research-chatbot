"""Oxford CEBM (Centre for Evidence-Based Medicine) levels-of-evidence
framework grader — the 1-5 therapy-hierarchy scale (1 = systematic
review of RCTs/RCT, 2 = cohort study, 3 = case-control study, 4 = case
series, 5 = expert opinion), adjusted one level worse when
risk_of_bias.overall_risk is HIGH (a "low-quality RCT" behaves like a
level-2 cohort study in CEBM's own guidance, and so on down the scale).

Study designs outside CEBM's therapy hierarchy (this pipeline's
classification.study_design spans non-medical designs too, e.g.
ALGORITHM/BENCHMARK from backend.classification.pass2's broader
taxonomy) fall back to level 5 — an honest "insufficient framework fit"
default, not a real determination of expert-opinion-level evidence.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..enums import GradeType, GradingFramework, RiskLevel
from ..interfaces import BaseFrameworkGrader
from ..models import FrameworkResult, Grade, GradeRationale, PrerequisiteAssessments

_LEVEL_BY_DESIGN = {
    StudyDesign.SYSTEMATIC_REVIEW: 1,
    StudyDesign.META_ANALYSIS: 1,
    StudyDesign.RCT: 1,
    StudyDesign.COHORT: 2,
    StudyDesign.OBSERVATIONAL: 2,
    StudyDesign.DIAGNOSTIC: 2,
    StudyDesign.CASE_CONTROL: 3,
    StudyDesign.CROSS_SECTIONAL: 3,
}
_FALLBACK_LEVEL = 5

_LEVEL_DESCRIPTIONS = {
    1: "systematic review of RCTs / RCT",
    2: "cohort study",
    3: "case-control study",
    4: "case series",
    5: "expert opinion / insufficient framework fit",
}

_ASSESSMENT_CONFIDENCE = 0.5


class OxfordGrader(BaseFrameworkGrader):
    """See module docstring."""

    def grade(
        self,
        prerequisites: PrerequisiteAssessments,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> FrameworkResult:
        base_level = _LEVEL_BY_DESIGN.get(classification.study_design.label, _FALLBACK_LEVEL)
        level = base_level
        rationale = [
            GradeRationale(
                rule_applied="base_level_by_study_design",
                evidence_used=[],
                confidence_impact=0.0,
                framework_source=GradingFramework.OXFORD.value,
                reasoning=f"study design {classification.study_design.label.value} -> base level {base_level}",
            )
        ]

        if prerequisites.risk_of_bias.overall_risk == RiskLevel.HIGH and level < _FALLBACK_LEVEL:
            level += 1
            rationale.append(
                GradeRationale(
                    rule_applied="high_risk_of_bias_adjustment",
                    evidence_used=prerequisites.risk_of_bias.evidence,
                    confidence_impact=-0.1,
                    framework_source=GradingFramework.OXFORD.value,
                    reasoning="high risk of bias -> downgraded one level",
                )
            )

        confidence = _ASSESSMENT_CONFIDENCE if prerequisites.risk_of_bias.confidence > 0.0 else 0.3
        evidence = list(prerequisites.risk_of_bias.evidence)

        grade = Grade(
            grade_type=GradeType.EVIDENCE_QUALITY,
            grade_value=str(level),
            grade_description=f"Oxford CEBM level {level}: {_LEVEL_DESCRIPTIONS[level]}",
            confidence=confidence,
            framework=GradingFramework.OXFORD,
            prerequisites_used=self.requires(),
            rationale=rationale,
            evidence=evidence,
        )

        return FrameworkResult(
            framework=GradingFramework.OXFORD,
            grade=grade,
            grade_result=None,
            confidence=confidence,
            evidence=evidence,
        )

    def framework(self) -> GradingFramework:
        return GradingFramework.OXFORD

    def requires(self) -> list[str]:
        return ["risk_of_bias"]

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 90

    def version(self) -> str:
        return "1.0.0"

    def compatible_frameworks(self) -> list[GradingFramework]:
        return [GradingFramework.GRADE, GradingFramework.NIH, GradingFramework.SIGN]
