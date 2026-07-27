"""Unit tests for framework graders."""

from backend.classification.pass2.enums import StudyDesign
from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.enums import (
    GRADEDowngradeFactor,
    GRADEQuality,
    GradingFramework,
    RecommendationStrength,
    RiskLevel,
)
from backend.evidence_grading.frameworks.grade import GRADEGrader
from backend.evidence_grading.frameworks.oxford import OxfordGrader
from backend.evidence_grading.models import (
    ConsistencyAssessment,
    DirectnessAssessment,
    PrecisionAssessment,
    PrerequisiteAssessments,
    PublicationBiasAssessment,
    RiskOfBiasAssessment,
)
from backend.medical_understanding.models import ConfidenceScore as MedicalConfidence
from backend.medical_understanding.models import MedicalUnderstanding


def _prereqs(**overrides) -> PrerequisiteAssessments:
    base = dict(
        risk_of_bias=RiskOfBiasAssessment(overall_risk=RiskLevel.LOW, confidence=0.8),
        consistency=ConsistencyAssessment(applicable=False),
        precision=PrecisionAssessment(confidence=0.7),
        directness=DirectnessAssessment(confidence=0.7),
        publication_bias=PublicationBiasAssessment(applicable=False),
    )
    base.update(overrides)
    return PrerequisiteAssessments(**base)


def _medical() -> MedicalUnderstanding:
    return MedicalUnderstanding(confidence=MedicalConfidence(overall=0.7, components={}, formula=""))


def test_grade_rct_starts_high(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["RCT methods.\n"]))
    result = GRADEGrader(EvidenceGradingConfig()).grade(
        _prereqs(),
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    assert result.framework == GradingFramework.GRADE
    assert result.grade_result is not None
    assert result.grade_result.initial_quality == GRADEQuality.HIGH
    assert result.grade_result.recommendation_strength is not None


def test_grade_downgrades_for_high_risk_of_bias(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Observational cohort.\n"]))
    prereqs = _prereqs(
        risk_of_bias=RiskOfBiasAssessment(
            overall_risk=RiskLevel.HIGH,
            downgrade_recommendation=True,
            downgrade_level=2,
            confidence=0.7,
        )
    )
    result = GRADEGrader(EvidenceGradingConfig()).grade(
        prereqs,
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    assert GRADEDowngradeFactor.RISK_OF_BIAS in result.grade_result.downgrade_factors
    assert result.grade_result.final_quality != GRADEQuality.HIGH


def test_grade_strong_recommendation_when_high_no_downgrades(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Well-conducted RCT.\n"]))
    result = GRADEGrader(EvidenceGradingConfig()).grade(
        _prereqs(),
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    assert result.grade_result.recommendation_strength == RecommendationStrength.STRONG


def test_oxford_maps_rct_to_level_1(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["RCT.\n"]))
    result = OxfordGrader().grade(
        _prereqs(),
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    assert result.framework == GradingFramework.OXFORD
    assert result.grade.grade_value.startswith("1") or result.grade.grade_value == "1"
