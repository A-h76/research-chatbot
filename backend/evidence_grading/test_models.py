from backend.evidence_grading.enums import GradingFramework
from backend.evidence_grading.models import ConfidenceScore, EvidenceGrades, PrerequisiteAssessments


def test_confidence_score_calculate_matches_formula():
    score = ConfidenceScore.calculate(
        evidence_support=0.8, framework_completeness=0.6, assessment_agreement=0.7, extraction_confidence=0.9
    )
    expected = 0.35 * 0.8 + 0.25 * 0.6 + 0.20 * 0.7 + 0.20 * 0.9
    assert score.overall == expected
    assert score.components["evidence_support"] == 0.8


def test_confidence_score_clamps_to_unit_interval():
    score = ConfidenceScore.calculate(1.0, 1.0, 1.0, 1.0)
    assert score.overall == 1.0
    score = ConfidenceScore.calculate(0.0, 0.0, 0.0, 0.0)
    assert score.overall == 0.0


def test_confidence_score_empty():
    empty = ConfidenceScore.empty()
    assert empty.overall == 0.0
    assert empty.components == {}


def test_prerequisite_assessments_defaults_construct():
    prereqs = PrerequisiteAssessments()
    assert prereqs.publication_bias is None
    assert prereqs.risk_of_bias.confidence == 0.0
    assert prereqs.confidence.overall == 0.0


def test_evidence_grades_skipped_fast_path():
    grades = EvidenceGrades(skipped=True, reasoning="evidence grading not required")
    assert grades.skipped is True
    assert grades.overall_grade.framework == GradingFramework.UNKNOWN
    assert grades.outcome_grades == {}


def test_evidence_grades_defaults_construct_standalone():
    grades = EvidenceGrades()
    assert grades.skipped is False
    assert grades.warnings == []
    assert grades.errors == []
