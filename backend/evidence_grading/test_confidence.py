"""Unit tests for deterministic confidence calculation."""

from backend.document_understanding.models import EvidenceReference
from backend.evidence_grading.confidence import compute_confidence
from backend.evidence_grading.models import ConfidenceScore, PrerequisiteAssessments, RiskOfBiasAssessment


def _ref() -> EvidenceReference:
    return EvidenceReference(
        page=1,
        section=None,
        paragraph=None,
        character_range=None,
        text_snippet="snippet",
        confidence=1.0,
    )


def test_compute_confidence_weights_match_formula():
    prerequisites = PrerequisiteAssessments(
        risk_of_bias=RiskOfBiasAssessment(confidence=1.0, evidence=[_ref()])
    )
    score = compute_confidence(
        prerequisites,
        enabled_framework_count=2,
        produced_framework_count=2,
        assessment_agreement=1.0,
        medical_confidence=1.0,
    )

    expected = ConfidenceScore.calculate(
        score.components["evidence_support"],
        score.components["framework_completeness"],
        score.components["assessment_agreement"],
        score.components["extraction_confidence"],
    )
    assert score.overall == expected.overall
    assert score.components["framework_completeness"] == 1.0
    assert score.components["assessment_agreement"] == 1.0
    assert score.components["evidence_support"] > 0.0


def test_framework_completeness_partial():
    score = compute_confidence(
        PrerequisiteAssessments(),
        enabled_framework_count=4,
        produced_framework_count=2,
        assessment_agreement=0.5,
        medical_confidence=0.5,
    )
    assert score.components["framework_completeness"] == 0.5


def test_zero_enabled_frameworks_gives_zero_completeness():
    score = compute_confidence(
        PrerequisiteAssessments(),
        enabled_framework_count=0,
        produced_framework_count=0,
        assessment_agreement=1.0,
        medical_confidence=0.0,
    )
    assert score.components["framework_completeness"] == 0.0
