"""Reporting quality assessment — CONSORT (RCTs), PRISMA (systematic
reviews), STROBE (observational studies), reusing classification's
already-classified ReportingGuideline (Phase 1.2) directly rather than
re-deriving which guideline applies.

Full checklist-item-by-item compliance scoring (CONSORT's 25 items,
PRISMA's 27, STROBE's 22) would require reading detailed methods/results
text against each specific item's own criteria — this module instead
checks a small subset of each guideline's most load-bearing items, using
data backend.medical_understanding already extracted plus a few targeted
text-presence checks. compliance_items maps each checked item to whether
it was found; missing_items lists whichever weren't.

Separate from evidence quality (see package docstring's Design Decision
3) — a well-reported study can still have high risk of bias, and a
poorly-reported one can still be methodologically sound; this assessment
never feeds directly into GRADEQuality/study_quality.
"""

import re
from typing import Callable

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import ReportingGuideline
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..interfaces import BasePrerequisiteAssessor
from ..models import ReportingQualityAssessment

_TRIAL_REGISTRATION_RE = re.compile(r"clinicaltrials\.gov|trial registration", re.IGNORECASE)
_FLOW_DIAGRAM_RE = re.compile(r"flow diagram", re.IGNORECASE)
_SEARCH_STRATEGY_RE = re.compile(r"search strategy", re.IGNORECASE)
_ELIGIBILITY_CRITERIA_RE = re.compile(r"eligibility criteria|inclusion criteria", re.IGNORECASE)
_SETTING_RE = re.compile(r"\bsetting\b", re.IGNORECASE)

_ComplianceCheck = Callable[[MedicalUnderstanding, str], bool]

_CONSORT_ITEMS: dict[str, _ComplianceCheck] = {
    "randomization_method_described": lambda medical, text: bool(
        medical.study_characteristics and medical.study_characteristics.randomization_method
    ),
    "blinding_described": lambda medical, text: bool(medical.study_characteristics and medical.study_characteristics.blinding),
    "sample_size_reported": lambda medical, text: bool(medical.populations and medical.populations[0].sample_size),
    "trial_registration_reported": lambda medical, text: bool(_TRIAL_REGISTRATION_RE.search(text)),
    "primary_outcome_defined": lambda medical, text: bool(medical.outcomes),
}

_PRISMA_ITEMS: dict[str, _ComplianceCheck] = {
    "search_strategy_described": lambda medical, text: bool(_SEARCH_STRATEGY_RE.search(text)),
    "eligibility_criteria_described": lambda medical, text: bool(_ELIGIBILITY_CRITERIA_RE.search(text)),
    "flow_diagram_mentioned": lambda medical, text: bool(_FLOW_DIAGRAM_RE.search(text)),
    "outcomes_defined": lambda medical, text: bool(medical.outcomes),
}

_STROBE_ITEMS: dict[str, _ComplianceCheck] = {
    "setting_described": lambda medical, text: bool(_SETTING_RE.search(text)),
    "eligibility_criteria_described": lambda medical, text: bool(_ELIGIBILITY_CRITERIA_RE.search(text)),
    "sample_size_reported": lambda medical, text: bool(medical.populations and medical.populations[0].sample_size),
    "outcomes_defined": lambda medical, text: bool(medical.outcomes),
}

_ITEMS_BY_GUIDELINE: dict[ReportingGuideline, dict[str, _ComplianceCheck]] = {
    ReportingGuideline.CONSORT: _CONSORT_ITEMS,
    ReportingGuideline.PRISMA: _PRISMA_ITEMS,
    ReportingGuideline.STROBE: _STROBE_ITEMS,
}

_ASSESSMENT_CONFIDENCE = 0.5


class ReportingQualityAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> ReportingQualityAssessment:
        guideline = classification.reporting_guideline.label
        items = _ITEMS_BY_GUIDELINE.get(guideline)
        if items is None:
            return ReportingQualityAssessment(reporting_guideline=guideline)

        compliance_items = {name: check(medical, document.full_text) for name, check in items.items()}
        missing_items = [name for name, met in compliance_items.items() if not met]
        score = 100.0 * sum(compliance_items.values()) / len(compliance_items)

        return ReportingQualityAssessment(
            reporting_quality_score=score,
            reporting_guideline=guideline,
            compliance_items=compliance_items,
            missing_items=missing_items,
            partially_met_items=[],
            confidence=_ASSESSMENT_CONFIDENCE,
            evidence=[],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 50
