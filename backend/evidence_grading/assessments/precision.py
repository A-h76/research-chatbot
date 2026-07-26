"""Precision assessment — confidence interval width and sample size,
derived entirely from backend.medical_understanding's already-extracted
StatisticalMeasure list and Population/DemographicData (no new text
scanning — Phase 1.4 already found these).

CI-width classification uses the upper/lower ratio for ratio-type
measures (HR/OR/RR) as a coarse imprecision proxy — a CI ratio this wide
(e.g. 1.02-2.07, ratio ~2) is a real, if approximate, "how much could
the true effect plausibly differ" signal without needing the original
point estimate.
"""

import re
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.enums import StatisticalMeasureType
from backend.medical_understanding.models import MedicalUnderstanding

from ..enums import PrecisionLevel
from ..interfaces import BasePrerequisiteAssessor
from ..models import ConfidenceInterval, EffectSize, PrecisionAssessment

_CI_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)")
_FIRST_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

_EFFECT_MEASURE_TYPES = frozenset(
    {
        StatisticalMeasureType.HAZARD_RATIO,
        StatisticalMeasureType.ODDS_RATIO,
        StatisticalMeasureType.RELATIVE_RISK,
        StatisticalMeasureType.MEAN_DIFFERENCE,
        StatisticalMeasureType.EFFECT_SIZE,
    }
)

# A ratio-measure effect this far from 1.0 (>=2x or <=0.5x) is
# conventionally treated as a "large effect" in GRADE's own guidance.
_LARGE_EFFECT_HIGH = 2.0
_LARGE_EFFECT_LOW = 0.5

# CI upper/lower ratio bands.
_NARROW_CI_RATIO = 2.0
_MODERATE_CI_RATIO = 4.0

_SMALL_SAMPLE_SIZE = 100
_ASSESSMENT_CONFIDENCE = 0.6


class PrecisionAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> PrecisionAssessment:
        effect_size = self._extract_effect_size(medical)
        confidence_interval = self._extract_confidence_interval(medical)
        sample_size = self._extract_sample_size(medical)

        precision_level, precision_score = self._classify(confidence_interval, sample_size)
        downgrade_level = 1 if precision_level == PrecisionLevel.LOW else 0
        has_signal = confidence_interval is not None or sample_size is not None

        return PrecisionAssessment(
            precision_score=precision_score,
            precision_level=precision_level,
            effect_size=effect_size,
            confidence_interval=confidence_interval,
            sample_size=sample_size,
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
    def _extract_effect_size(medical: MedicalUnderstanding) -> Optional[EffectSize]:
        for measure in medical.statistical_measures:
            if measure.measure_type not in _EFFECT_MEASURE_TYPES:
                continue
            match = _FIRST_NUMBER_RE.search(measure.value)
            if match is None:
                continue
            numeric = float(match.group(0))
            return EffectSize(
                measure_type=measure.measure_type,
                value=numeric,
                is_large_effect=numeric >= _LARGE_EFFECT_HIGH or numeric <= _LARGE_EFFECT_LOW,
            )
        return None

    @staticmethod
    def _extract_confidence_interval(medical: MedicalUnderstanding) -> Optional[ConfidenceInterval]:
        for measure in medical.statistical_measures:
            if measure.measure_type != StatisticalMeasureType.CONFIDENCE_INTERVAL:
                continue
            match = _CI_RANGE_RE.search(measure.value)
            if match is None:
                continue
            return ConfidenceInterval(lower=float(match.group(1)), upper=float(match.group(2)))
        return None

    @staticmethod
    def _extract_sample_size(medical: MedicalUnderstanding) -> Optional[int]:
        if medical.demographic_data is not None and medical.demographic_data.total_participants is not None:
            return medical.demographic_data.total_participants
        if medical.populations and medical.populations[0].sample_size is not None:
            return medical.populations[0].sample_size
        return None

    @staticmethod
    def _classify(ci: Optional[ConfidenceInterval], sample_size: Optional[int]) -> tuple[PrecisionLevel, float]:
        ci_level: Optional[PrecisionLevel] = None
        ci_score = 0.0
        if ci is not None and ci.lower > 0:
            ratio = ci.upper / ci.lower
            if ratio <= _NARROW_CI_RATIO:
                ci_level, ci_score = PrecisionLevel.HIGH, 0.9
            elif ratio <= _MODERATE_CI_RATIO:
                ci_level, ci_score = PrecisionLevel.MODERATE, 0.6
            else:
                ci_level, ci_score = PrecisionLevel.LOW, 0.2

        small_sample = sample_size is not None and sample_size < _SMALL_SAMPLE_SIZE

        if ci_level is None and sample_size is None:
            return PrecisionLevel.UNKNOWN, 0.0
        if small_sample and ci_level != PrecisionLevel.HIGH:
            return PrecisionLevel.LOW, 0.3
        if ci_level is not None:
            return ci_level, ci_score
        return PrecisionLevel.MODERATE, 0.5
