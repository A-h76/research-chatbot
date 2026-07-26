"""GRADE (Grading of Recommendations Assessment, Development and
Evaluation) framework grader.

Initial quality comes from config.grade_initial_quality_mapping, keyed
by classification.study_design.label's own string value ("rct",
"observational", "systematic_review", ...); META_ANALYSIS is treated
like SYSTEMATIC_REVIEW (both start HIGH per GRADE convention), and any
other design not in the mapping defaults to LOW — GRADE's own rule that
all observational-family designs start low regardless of subtype.

The 5 standard downgrade factors are read off the matching prerequisite
assessment's own downgrade_recommendation/downgrade_level (already
computed by assessments/*.py — this module never re-derives risk-of-
bias/inconsistency/imprecision signal, only consumes it). The 3 upgrade
factors only apply when initial_quality started LOW/VERY_LOW (GRADE
never upgrades a study that started HIGH); LARGE_EFFECT reads
prerequisites.precision.effect_size.is_large_effect directly, while
DOSE_RESPONSE/RESIDUAL_CONFOUNDING have no corresponding upstream field
anywhere in Phase 1.4, so they fall back to a plain text-mention check —
an honest proxy for "was this ever discussed", not a real dose-response
or confounding analysis.

GRADEFrameworkResult.downgrade_factors/upgrade_factors name *which*
factors applied, not their magnitude — each contributing assessment's
own downgrade_level (0/1/2, matching GRADE's "serious"/"very serious"
convention) is instead reflected in this module's own GradeRationale.
confidence_impact entries for detailed traceability. AuditTrail
recording (record_downgrade/record_upgrade in audit.py) happens once in
pipeline.py after collecting every framework's result, using the
simpler "1 level per named factor" convention audit.py already
documents as a fixed constant, not a re-derivation of magnitude.
"""

import re

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import EvidenceGradingConfig
from ..enums import (
    GradeType,
    GradingFramework,
    GRADEDowngradeFactor,
    GRADEQuality,
    GRADEUpgradeFactor,
    RecommendationStrength,
)
from ..interfaces import BaseFrameworkGrader
from ..models import FrameworkResult, Grade, GradeRationale, GRADEFrameworkResult, PrerequisiteAssessments

_QUALITY_ORDER = [GRADEQuality.VERY_LOW, GRADEQuality.LOW, GRADEQuality.MODERATE, GRADEQuality.HIGH]

_DOSE_RESPONSE_RE = re.compile(r"dose[\s-]response", re.IGNORECASE)
_RESIDUAL_CONFOUNDING_RE = re.compile(r"residual confound", re.IGNORECASE)

_CONFIDENCE_IMPACT_PER_LEVEL = 0.1


class GRADEGrader(BaseFrameworkGrader):
    """See module docstring."""

    def __init__(self, config: EvidenceGradingConfig) -> None:
        self._config = config

    def grade(
        self,
        prerequisites: PrerequisiteAssessments,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> FrameworkResult:
        initial_quality = self._initial_quality(classification.study_design.label)
        ordinal = _QUALITY_ORDER.index(initial_quality)

        rationale: list[GradeRationale] = []
        downgrade_factors, ordinal = self._apply_downgrades(prerequisites, ordinal, rationale)

        upgrade_factors: list[GRADEUpgradeFactor] = []
        if initial_quality in (GRADEQuality.LOW, GRADEQuality.VERY_LOW):
            upgrade_factors, ordinal = self._apply_upgrades(prerequisites, document, ordinal, rationale)

        final_quality = _QUALITY_ORDER[max(0, min(len(_QUALITY_ORDER) - 1, ordinal))]
        recommendation_strength = self._recommendation_strength(final_quality, downgrade_factors)

        used_confidences = self._used_confidences(prerequisites, downgrade_factors)
        confidence = sum(used_confidences) / len(used_confidences) if used_confidences else 0.0
        evidence = self._collect_evidence(prerequisites)

        grade_result = GRADEFrameworkResult(
            evidence_quality=final_quality,
            recommendation_strength=recommendation_strength,
            downgrade_factors=downgrade_factors,
            upgrade_factors=upgrade_factors,
            initial_quality=initial_quality,
            final_quality=final_quality,
            rationale=rationale,
            confidence=confidence,
            evidence=evidence,
        )

        grade = Grade(
            grade_type=GradeType.EVIDENCE_QUALITY,
            grade_value=final_quality.value,
            grade_description=f"GRADE evidence quality: {final_quality.value}",
            confidence=confidence,
            framework=GradingFramework.GRADE,
            prerequisites_used=self.requires(),
            rationale=rationale,
            evidence=evidence,
        )

        return FrameworkResult(
            framework=GradingFramework.GRADE,
            grade=grade,
            grade_result=grade_result,
            confidence=confidence,
            evidence=evidence,
        )

    def framework(self) -> GradingFramework:
        return GradingFramework.GRADE

    def requires(self) -> list[str]:
        return ["risk_of_bias", "consistency", "precision", "directness", "publication_bias"]

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 100

    def version(self) -> str:
        return "1.0.0"

    def compatible_frameworks(self) -> list[GradingFramework]:
        return [GradingFramework.OXFORD, GradingFramework.NIH, GradingFramework.SIGN]

    @staticmethod
    def _recommendation_strength(
        final_quality: GRADEQuality, downgrade_factors: list[GRADEDowngradeFactor]
    ) -> RecommendationStrength:
        """Deterministic GRADE recommendation-strength proxy without
        benefit/harm trade-off data (Phase 1.4 doesn't extract that).
        HIGH/MODERATE with no downgrades → STRONG; otherwise WEAK."""
        if final_quality in (GRADEQuality.HIGH, GRADEQuality.MODERATE) and not downgrade_factors:
            return RecommendationStrength.STRONG
        return RecommendationStrength.WEAK

    def _initial_quality(self, study_design: StudyDesign) -> GRADEQuality:
        if study_design == StudyDesign.META_ANALYSIS:
            key = StudyDesign.SYSTEMATIC_REVIEW.value
        else:
            key = study_design.value
        return self._config.grade_initial_quality_mapping.get(key, GRADEQuality.LOW)

    @staticmethod
    def _apply_downgrades(
        prerequisites: PrerequisiteAssessments, ordinal: int, rationale: list[GradeRationale]
    ) -> tuple[list[GRADEDowngradeFactor], int]:
        factors: list[GRADEDowngradeFactor] = []

        candidates = [
            (GRADEDowngradeFactor.RISK_OF_BIAS, prerequisites.risk_of_bias, True),
            (GRADEDowngradeFactor.INCONSISTENCY, prerequisites.consistency, prerequisites.consistency.applicable),
            (GRADEDowngradeFactor.INDIRECTNESS, prerequisites.directness, True),
            (GRADEDowngradeFactor.IMPRECISION, prerequisites.precision, True),
            (
                GRADEDowngradeFactor.PUBLICATION_BIAS,
                prerequisites.publication_bias,
                prerequisites.publication_bias is not None and prerequisites.publication_bias.applicable,
            ),
        ]

        for factor, assessment, applicable in candidates:
            if not applicable or assessment is None or not assessment.downgrade_recommendation:
                continue
            levels = max(1, assessment.downgrade_level)
            ordinal -= levels
            factors.append(factor)
            rationale.append(
                GradeRationale(
                    rule_applied=factor.value,
                    evidence_used=assessment.evidence,
                    confidence_impact=-_CONFIDENCE_IMPACT_PER_LEVEL * levels,
                    framework_source=GradingFramework.GRADE.value,
                    reasoning=f"downgraded {levels} level(s) for {factor.value}",
                )
            )

        return factors, ordinal

    @staticmethod
    def _apply_upgrades(
        prerequisites: PrerequisiteAssessments,
        document: ProcessedDocument,
        ordinal: int,
        rationale: list[GradeRationale],
    ) -> tuple[list[GRADEUpgradeFactor], int]:
        factors: list[GRADEUpgradeFactor] = []

        large_effect = prerequisites.precision.effect_size is not None and prerequisites.precision.effect_size.is_large_effect
        dose_response = bool(_DOSE_RESPONSE_RE.search(document.full_text))
        residual_confounding = bool(_RESIDUAL_CONFOUNDING_RE.search(document.full_text))

        for factor, applies in (
            (GRADEUpgradeFactor.LARGE_EFFECT, large_effect),
            (GRADEUpgradeFactor.DOSE_RESPONSE, dose_response),
            (GRADEUpgradeFactor.RESIDUAL_CONFOUNDING, residual_confounding),
        ):
            if not applies:
                continue
            ordinal += 1
            factors.append(factor)
            rationale.append(
                GradeRationale(
                    rule_applied=factor.value,
                    evidence_used=prerequisites.precision.evidence,
                    confidence_impact=_CONFIDENCE_IMPACT_PER_LEVEL,
                    framework_source=GradingFramework.GRADE.value,
                    reasoning=f"upgraded 1 level for {factor.value}",
                )
            )

        return factors, ordinal

    @staticmethod
    def _used_confidences(prerequisites: PrerequisiteAssessments, downgrade_factors: list) -> list[float]:
        confidences = [prerequisites.risk_of_bias.confidence, prerequisites.directness.confidence, prerequisites.precision.confidence]
        if prerequisites.consistency.applicable:
            confidences.append(prerequisites.consistency.confidence)
        if prerequisites.publication_bias is not None and prerequisites.publication_bias.applicable:
            confidences.append(prerequisites.publication_bias.confidence)
        return [c for c in confidences if c > 0.0]

    @staticmethod
    def _collect_evidence(prerequisites: PrerequisiteAssessments) -> list:
        evidence = list(prerequisites.risk_of_bias.evidence) + list(prerequisites.directness.evidence) + list(prerequisites.precision.evidence)
        if prerequisites.consistency.applicable:
            evidence += list(prerequisites.consistency.evidence)
        if prerequisites.publication_bias is not None and prerequisites.publication_bias.applicable:
            evidence += list(prerequisites.publication_bias.evidence)
        return evidence
