"""Directness assessment — population/intervention/comparator/outcome
match scores.

This pipeline's own inputs (document, classification, context, medical)
have no separate "target review question" to compare the study's PICO
against — directness here is instead a proxy for how completely and
confidently each PICO element was itself extracted by Phase 1.4: a
study whose population/intervention/comparator/outcome were all clearly
and confidently identified answers a PICO-shaped question directly; one
where these are missing or low-confidence is, from this pipeline's own
evidence, indirect (we can't even confirm what was studied, let alone
whether it matches a target question).
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..enums import DirectnessLevel
from ..interfaces import BasePrerequisiteAssessor
from ..models import DirectnessAssessment

_DIRECT_THRESHOLD = 0.7
_MODERATELY_DIRECT_THRESHOLD = 0.4

_ASSESSMENT_CONFIDENCE = 0.5


class DirectnessAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> DirectnessAssessment:
        population_match = self._mean_confidence([medical.populations[0]] if medical.populations else [])
        intervention_match = self._mean_confidence(medical.interventions)
        comparator_match = self._mean_confidence(medical.comparators)
        outcome_match = self._mean_confidence(medical.outcomes)

        directness_score = (population_match + intervention_match + comparator_match + outcome_match) / 4
        directness_level = self._level(directness_score)
        downgrade_level = 1 if directness_level == DirectnessLevel.INDIRECT else 0
        has_signal = bool(medical.populations or medical.interventions or medical.comparators or medical.outcomes)

        return DirectnessAssessment(
            directness_score=directness_score,
            directness_level=directness_level,
            population_match=population_match,
            intervention_match=intervention_match,
            comparator_match=comparator_match,
            outcome_match=outcome_match,
            downgrade_recommendation=downgrade_level > 0,
            downgrade_level=downgrade_level,
            confidence=_ASSESSMENT_CONFIDENCE if has_signal else 0.0,
            evidence=[],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 50

    @staticmethod
    def _mean_confidence(items: list) -> float:
        if not items:
            return 0.0
        return sum(item.confidence for item in items) / len(items)

    @staticmethod
    def _level(score: float) -> DirectnessLevel:
        if score >= _DIRECT_THRESHOLD:
            return DirectnessLevel.DIRECT
        if score >= _MODERATELY_DIRECT_THRESHOLD:
            return DirectnessLevel.MODERATELY_DIRECT
        if score > 0.0:
            return DirectnessLevel.INDIRECT
        return DirectnessLevel.UNAVAILABLE
