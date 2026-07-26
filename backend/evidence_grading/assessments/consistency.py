"""Consistency assessment — I² heterogeneity statistic and Cochran's
Q-test p-value, only applicable to systematic reviews/meta-analyses (see
config.consistency_only_reviews) — a single primary study has no
"consistency across studies" to assess at all.

I²/Q-test values aren't part of backend.medical_understanding's own
StatisticalMeasureType (Phase 1.4 has no dedicated heterogeneity-measure
type) — this module does its own small, targeted regex search over the
document text for these two specific patterns, the same "a prerequisite
assessor may look for signals Phase 1.4 didn't capture" precedent
assessments/risk_of_bias.py already establishes for ITT/blinding/
registration mentions.

Thresholds match the Cochrane Handbook's own conventional I² bands:
<50% not important/low, 50-75% substantial/moderate, >=75% considerable.
"""

import re
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import EvidenceGradingConfig
from ..enums import ConsistencyLevel
from ..interfaces import BasePrerequisiteAssessor
from ..models import ConsistencyAssessment

_REVIEW_DESIGNS = frozenset({StudyDesign.SYSTEMATIC_REVIEW, StudyDesign.META_ANALYSIS})

_I_SQUARED_RE = re.compile(r"I\s*[²2]\s*=\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_Q_TEST_RE = re.compile(r"(?:Q[\s-]test|heterogeneity)[^.]{0,40}?p\s*[=<]\s*(0?\.\d+)", re.IGNORECASE)

_HIGH_HETEROGENEITY_THRESHOLD = 75.0
_MODERATE_HETEROGENEITY_THRESHOLD = 50.0

_ASSESSMENT_CONFIDENCE = 0.6


class ConsistencyAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def __init__(self, config: Optional[EvidenceGradingConfig] = None) -> None:
        self._config = config or EvidenceGradingConfig()

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> ConsistencyAssessment:
        if self._config.consistency_only_reviews and classification.study_design.label not in _REVIEW_DESIGNS:
            return ConsistencyAssessment(applicable=False, consistency_level=ConsistencyLevel.UNAVAILABLE)

        heterogeneity = self._extract_i_squared(document.full_text)
        p_value = self._extract_q_test(document.full_text)

        if heterogeneity is None:
            level, score = ConsistencyLevel.UNKNOWN, 0.0
        elif heterogeneity >= _HIGH_HETEROGENEITY_THRESHOLD:
            level, score = ConsistencyLevel.INCONSISTENT, 0.2
        elif heterogeneity >= _MODERATE_HETEROGENEITY_THRESHOLD:
            level, score = ConsistencyLevel.MODERATELY_CONSISTENT, 0.6
        else:
            level, score = ConsistencyLevel.HIGHLY_CONSISTENT, 0.9

        downgrade_level = 1 if level == ConsistencyLevel.INCONSISTENT else 0

        return ConsistencyAssessment(
            consistency_score=score,
            consistency_level=level,
            heterogeneity=heterogeneity,
            p_value=p_value,
            findings=[f"I² = {heterogeneity}%"] if heterogeneity is not None else [],
            applicable=True,
            downgrade_recommendation=downgrade_level > 0,
            downgrade_level=downgrade_level,
            confidence=_ASSESSMENT_CONFIDENCE if heterogeneity is not None else 0.0,
            evidence=[],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 50

    @staticmethod
    def _extract_i_squared(text: str) -> Optional[float]:
        match = _I_SQUARED_RE.search(text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _extract_q_test(text: str) -> Optional[float]:
        match = _Q_TEST_RE.search(text)
        return float(match.group(1)) if match else None
