"""Outcome-specific grade assembly.

Real GRADE practice grades each outcome separately, using outcome-
specific effect estimates and precision. This pipeline's frameworks
(frameworks/*.py) only ever produce one document-level grade — nothing
upstream (backend.medical_understanding's Outcome model) carries a
per-outcome effect size/CI pairing that would let a framework grade
each outcome independently. Rather than fabricate per-outcome framework
runs this pipeline has no real signal for, each outcome named by Phase
1.4 gets the same document-level aggregated Grade, with its own
per-outcome confidence capped by that outcome's own extraction
confidence — an honest "we know this much about THIS outcome
specifically" signal layered on top of the shared grade, not an
independent re-grading.
"""

from backend.medical_understanding.models import MedicalUnderstanding

from ..models import EvidenceReference, Grade, OutcomeGrade


def aggregate_outcomes(
    medical: MedicalUnderstanding,
    overall_grade: Grade,
) -> dict[str, OutcomeGrade]:
    outcome_grades: dict[str, OutcomeGrade] = {}
    for outcome in medical.outcomes:
        evidence: list[EvidenceReference] = [outcome.evidence] if outcome.evidence is not None else []
        outcome_grades[outcome.name] = OutcomeGrade(
            outcome_name=outcome.name,
            grade=overall_grade,
            confidence=min(overall_grade.confidence, outcome.confidence) if outcome.confidence > 0.0 else overall_grade.confidence,
            evidence=evidence,
        )
    return outcome_grades
