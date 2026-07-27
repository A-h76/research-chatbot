"""Publication bias assessment — only applicable to systematic reviews/
meta-analyses (see config.publication_bias_only_reviews). Real funnel-
plot asymmetry detection requires per-study effect-size/precision data
this pipeline doesn't have (a single document's extracted text, not a
meta-analysis's underlying dataset) — this instead detects whether the
document itself reports having assessed publication bias at all (funnel
plot, Egger's test, ...), a proxy for "was this even checked", not an
independent determination of asymmetry.
"""

import re
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import EvidenceGradingConfig
from ..enums import RiskLevel
from ..interfaces import BasePrerequisiteAssessor
from ..models import PublicationBiasAssessment

_REVIEW_DESIGNS = frozenset({StudyDesign.SYSTEMATIC_REVIEW, StudyDesign.META_ANALYSIS})

_FUNNEL_PLOT_RE = re.compile(r"funnel plot", re.IGNORECASE)
_EGGER_TEST_RE = re.compile(r"egger'?s? test", re.IGNORECASE)
_ASYMMETRY_RE = re.compile(r"asymmetr", re.IGNORECASE)
_SMALL_STUDY_RE = re.compile(r"small[\s-]study effects?", re.IGNORECASE)

_ASSESSMENT_CONFIDENCE = 0.5


class PublicationBiasAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def __init__(self, config: Optional[EvidenceGradingConfig] = None) -> None:
        self._config = config or EvidenceGradingConfig()

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> PublicationBiasAssessment:
        if self._config.publication_bias_only_reviews and classification.study_design.label not in _REVIEW_DESIGNS:
            return PublicationBiasAssessment(applicable=False)

        text = document.full_text
        assessed = bool(_FUNNEL_PLOT_RE.search(text) or _EGGER_TEST_RE.search(text))
        asymmetry_found = bool(_ASYMMETRY_RE.search(text)) if assessed else None
        small_study_effects = bool(_SMALL_STUDY_RE.search(text)) if assessed else None

        if not assessed:
            risk_level = RiskLevel.UNCLEAR
        elif asymmetry_found or small_study_effects:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.LOW

        downgrade_level = 1 if risk_level == RiskLevel.HIGH else 0

        return PublicationBiasAssessment(
            risk_level=risk_level,
            applicable=True,
            funnel_plot_asymmetry=asymmetry_found,
            small_study_effects=small_study_effects,
            downgrade_recommendation=downgrade_level > 0,
            downgrade_level=downgrade_level,
            confidence=_ASSESSMENT_CONFIDENCE if assessed else 0.0,
            evidence=[],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 50
