"""Unit tests for aggregators and conflict resolution."""

from backend.evidence_grading.aggregators.conflict_resolver import (
    agreement_score,
    detect_and_resolve,
    normalize_grade,
)
from backend.evidence_grading.aggregators.grade_aggregator import aggregate_grade
from backend.evidence_grading.aggregators.outcome_aggregator import aggregate_outcomes
from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.enums import AggregationStrategy, GradeType, GradingFramework
from backend.evidence_grading.models import FrameworkResult, Grade
from backend.medical_understanding.models import ConfidenceScore as MedicalConfidence
from backend.medical_understanding.models import MedicalUnderstanding, Outcome


def _result(framework: GradingFramework, value: str, confidence: float = 0.8) -> FrameworkResult:
    return FrameworkResult(
        framework=framework,
        grade=Grade(
            grade_type=GradeType.EVIDENCE_QUALITY,
            grade_value=value,
            confidence=confidence,
            framework=framework,
        ),
        confidence=confidence,
    )


def test_normalize_grade_positions():
    assert normalize_grade(GradingFramework.GRADE, "high") == 1.0
    assert normalize_grade(GradingFramework.GRADE, "very_low") == 0.0
    assert normalize_grade(GradingFramework.OXFORD, "1") == 1.0


def test_detect_conflict_and_resolve_conservative():
    results = {
        GradingFramework.GRADE: _result(GradingFramework.GRADE, "high"),
        GradingFramework.OXFORD: _result(GradingFramework.OXFORD, "5"),
    }
    config = EvidenceGradingConfig(conflict_resolution_strategy="conservative")
    conflict, position = detect_and_resolve(results, config)
    assert conflict is not None
    assert conflict.resolution_strategy == "conservative"
    assert position == 0.0  # Oxford 5 is worst


def test_agreement_score_identical_is_one():
    results = {
        GradingFramework.GRADE: _result(GradingFramework.GRADE, "high"),
        GradingFramework.NIH: _result(GradingFramework.NIH, "good"),
    }
    assert agreement_score(results) == 1.0


def test_aggregate_weighted_average():
    results = {
        GradingFramework.GRADE: _result(GradingFramework.GRADE, "high"),
        GradingFramework.OXFORD: _result(GradingFramework.OXFORD, "3"),
    }
    config = EvidenceGradingConfig(aggregation_strategy=AggregationStrategy.WEIGHTED_AVERAGE)
    log = aggregate_grade(results, config)
    assert log.final_grade.grade_value in ("high", "moderate", "low", "very_low")
    assert log.aggregation_strategy == AggregationStrategy.WEIGHTED_AVERAGE
    assert set(log.inputs) == {"grade", "oxford"}


def test_aggregate_minimum_is_conservative():
    results = {
        GradingFramework.GRADE: _result(GradingFramework.GRADE, "high"),
        GradingFramework.OXFORD: _result(GradingFramework.OXFORD, "5"),
    }
    config = EvidenceGradingConfig(aggregation_strategy=AggregationStrategy.MINIMUM)
    log = aggregate_grade(results, config)
    assert log.final_grade.grade_value == "very_low"


def test_outcome_aggregator_copies_document_grade():
    overall = Grade(grade_value="moderate", confidence=0.9)
    medical = MedicalUnderstanding(
        confidence=MedicalConfidence(overall=0.7, components={}, formula=""),
        outcomes=[Outcome(name="HbA1c", confidence=0.5), Outcome(name="mortality", confidence=0.8)],
    )
    grades = aggregate_outcomes(medical, overall)
    assert set(grades) == {"HbA1c", "mortality"}
    assert grades["HbA1c"].grade is overall
    assert grades["HbA1c"].confidence == 0.5
    assert grades["mortality"].confidence == 0.8
