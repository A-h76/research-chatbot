"""Deterministic confidence calculation — computes the four inputs
ConfidenceScore.calculate() (models.py) combines into one overall score,
matching config.py's own confidence_formula string exactly.

- evidence_support: how much evidence backs the grading, scaled against
  a target count rather than reported raw (so a handful of references
  on a short case report isn't penalized the way a 40-page systematic
  review with the same count would be).
- framework_completeness: fraction of enabled frameworks that actually
  produced a result (vs failed or were skipped).
- assessment_agreement: passed in from aggregators/conflict_resolver.py,
  which already computes cross-framework normalized-quality agreement
  as part of conflict detection — not recomputed here, to avoid
  duplicating that cross-framework comparison logic in two places.
- extraction_confidence: the mean of the underlying prerequisite
  assessments' own confidence plus Phase 1.4's medical-understanding
  confidence — "how much do we trust the data this grading was built
  from", distinct from this phase's own grading logic.
"""

from .models import ConfidenceScore, PrerequisiteAssessments

# A target evidence-reference count beyond which more evidence stops
# adding confidence — deliberately modest, matching backend.
# medical_understanding.confidence's identical reasoning for entities.
_TARGET_EVIDENCE_COUNT = 10

_PREREQUISITE_FIELDS = (
    "risk_of_bias",
    "consistency",
    "precision",
    "directness",
    "publication_bias",
    "reporting_quality",
    "applicability",
)


def compute_confidence(
    prerequisites: PrerequisiteAssessments,
    enabled_framework_count: int,
    produced_framework_count: int,
    assessment_agreement: float,
    medical_confidence: float,
) -> ConfidenceScore:
    return ConfidenceScore.calculate(
        evidence_support=_evidence_support(prerequisites),
        framework_completeness=_framework_completeness(enabled_framework_count, produced_framework_count),
        assessment_agreement=max(0.0, min(1.0, assessment_agreement)),
        extraction_confidence=_extraction_confidence(prerequisites, medical_confidence),
    )


def _assessments(prerequisites: PrerequisiteAssessments) -> list:
    return [
        assessment
        for assessment in (getattr(prerequisites, name) for name in _PREREQUISITE_FIELDS)
        if assessment is not None
    ]


def _evidence_support(prerequisites: PrerequisiteAssessments) -> float:
    count = len(prerequisites.evidence)
    for assessment in _assessments(prerequisites):
        count += len(assessment.evidence)
    return min(count / _TARGET_EVIDENCE_COUNT, 1.0)


def _framework_completeness(enabled_count: int, produced_count: int) -> float:
    if enabled_count <= 0:
        return 0.0
    return min(produced_count / enabled_count, 1.0)


def _extraction_confidence(prerequisites: PrerequisiteAssessments, medical_confidence: float) -> float:
    confidences = [medical_confidence] + [assessment.confidence for assessment in _assessments(prerequisites)]
    return sum(confidences) / len(confidences)
