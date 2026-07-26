"""Unit tests for prerequisite assessors."""

from backend.classification.pass2.enums import StudyDesign
from backend.evidence_grading.assessments.consistency import ConsistencyAssessor
from backend.evidence_grading.assessments.publication_bias import PublicationBiasAssessor
from backend.evidence_grading.assessments.risk_of_bias import RiskOfBiasAssessor
from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.enums import ConsistencyLevel, RiskAssessmentTool, RiskLevel
from backend.medical_understanding.models import MedicalUnderstanding, ConfidenceScore as MedicalConfidence


def _medical() -> MedicalUnderstanding:
    return MedicalUnderstanding(
        confidence=MedicalConfidence(overall=0.5, components={}, formula=""),
    )


def test_risk_of_bias_uses_rob2_for_rcts(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(
        pdf_factory(
            [
                "Patients were randomly assigned. Double-blind. "
                "Intention-to-treat analysis. Registered at clinicaltrials.gov.\n"
            ]
        )
    )
    result = RiskOfBiasAssessor().assess(
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    assert result.assessment_tool == RiskAssessmentTool.ROB2
    assert result.overall_risk in (RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.UNCLEAR, RiskLevel.HIGH)
    assert result.domains


def test_consistency_not_applicable_for_rct(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["I² = 80% heterogeneity.\n"]))
    result = ConsistencyAssessor().assess(
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    assert result.applicable is False
    assert result.consistency_level == ConsistencyLevel.UNAVAILABLE


def test_consistency_extracts_i_squared_for_reviews(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Meta-analysis found I² = 82% across trials.\n"]))
    result = ConsistencyAssessor().assess(
        document,
        classification_factory(study_design=StudyDesign.META_ANALYSIS),
        _medical(),
    )
    assert result.applicable is True
    assert result.heterogeneity == 82.0
    assert result.consistency_level == ConsistencyLevel.INCONSISTENT
    assert result.downgrade_recommendation is True


def test_publication_bias_respects_config_flag(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Funnel plot showed asymmetry.\n"]))
    config = EvidenceGradingConfig(publication_bias_only_reviews=False)
    result = PublicationBiasAssessor(config).assess(
        document,
        classification_factory(study_design=StudyDesign.RCT),
        _medical(),
    )
    # With only_reviews=False, RCT is treated as applicable
    assert result.applicable is True


def test_publication_bias_detects_asymmetry_in_reviews(pdf_factory, classification_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Funnel plot asymmetry suggested publication bias.\n"]))
    result = PublicationBiasAssessor().assess(
        document,
        classification_factory(study_design=StudyDesign.SYSTEMATIC_REVIEW),
        _medical(),
    )
    assert result.applicable is True
    assert result.funnel_plot_asymmetry is True
    assert result.risk_level == RiskLevel.HIGH
