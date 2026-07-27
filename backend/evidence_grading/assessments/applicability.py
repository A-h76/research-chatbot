"""Applicability assessment — how generalizable this evidence is to
real-world clinical practice, distinct from DirectnessAssessment's
narrower PICO-matching (population/intervention/comparator/outcome). No
field-level spec was given for this model anywhere in the task (see
models.py's own module docstring) — this is a light, honestly-scoped
heuristic built from backend.medical_understanding's already-extracted
Population/StudyCharacteristics (no new text scanning): fewer exclusion
criteria and a multicenter design both suggest broader real-world
applicability; many exclusion criteria and a single-center design
suggest narrower.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..interfaces import BasePrerequisiteAssessor
from ..models import ApplicabilityAssessment

# More exclusion criteria than this suggests a narrowly-selected trial
# population, unlikely to generalize well to routine clinical practice.
_HIGH_EXCLUSION_COUNT = 5

_NARROW_POPULATION_SCORE = 0.3
_SOME_EXCLUSIONS_SCORE = 0.6
_UNKNOWN_SCORE = 0.5
_MULTICENTER_SCORE = 0.8
_SINGLE_CENTER_SCORE = 0.4

# A coarse heuristic, not a validated applicability tool — confidence is
# capped accordingly even when signals are found.
_ASSESSMENT_CONFIDENCE = 0.5


class ApplicabilityAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> ApplicabilityAssessment:
        concerns: list[str] = []

        population_generalizability = _UNKNOWN_SCORE
        evidence = []
        if medical.populations:
            population = medical.populations[0]
            exclusion_count = len(population.exclusion_criteria)
            if exclusion_count > _HIGH_EXCLUSION_COUNT:
                population_generalizability = _NARROW_POPULATION_SCORE
                concerns.append(f"{exclusion_count} exclusion criteria suggest a narrowly-selected population")
            elif exclusion_count > 0:
                population_generalizability = _SOME_EXCLUSIONS_SCORE
            if population.evidence is not None:
                evidence.append(population.evidence)

        setting_generalizability = _UNKNOWN_SCORE
        if medical.study_characteristics is not None:
            multicenter = medical.study_characteristics.multicenter
            if multicenter is True:
                setting_generalizability = _MULTICENTER_SCORE
            elif multicenter is False:
                setting_generalizability = _SINGLE_CENTER_SCORE
                concerns.append("single-center design may limit generalizability across settings")

        has_signal = bool(medical.populations) or medical.study_characteristics is not None
        confidence = _ASSESSMENT_CONFIDENCE if has_signal else 0.0

        return ApplicabilityAssessment(
            applicability_score=(population_generalizability + setting_generalizability) / 2,
            setting_generalizability=setting_generalizability,
            population_generalizability=population_generalizability,
            concerns=concerns,
            confidence=confidence,
            evidence=evidence,
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 50
