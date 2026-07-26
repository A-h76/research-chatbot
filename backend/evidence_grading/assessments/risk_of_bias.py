"""Risk of bias assessment — RoB2 (Cochrane Risk of Bias 2.0) for RCTs,
Newcastle-Ottawa Scale for observational studies (cohort/case-control/
cross-sectional). Reuses backend.medical_understanding's already-
extracted StudyCharacteristics/Population/document text — no new
extraction pass, only deterministic domain-level inference from what
Phase 1.4 already found.

Every domain-level signal here is a real, defensible but coarse proxy,
not full RoB2/NOS assessor judgment (which requires reading the full
methods section and applying detailed signalling questions a human
reviewer answers) — each domain's own docstring below names exactly what
it checks and what it can't. Domains with no available signal are rated
UNCLEAR, never guessed as LOW or HIGH.
"""

import re

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from ..enums import BiasType, RiskAssessmentTool, RiskLevel
from ..interfaces import BasePrerequisiteAssessor
from ..models import RiskDomain, RiskOfBiasAssessment

_RCT_DESIGNS = frozenset({StudyDesign.RCT})
_OBSERVATIONAL_DESIGNS = frozenset(
    {StudyDesign.COHORT, StudyDesign.CASE_CONTROL, StudyDesign.CROSS_SECTIONAL, StudyDesign.OBSERVATIONAL}
)

_ITT_RE = re.compile(r"intention[\s-]to[\s-]treat", re.IGNORECASE)
_REGISTRATION_RE = re.compile(r"clinicaltrials\.gov|trial registration|registered (?:at|with)", re.IGNORECASE)
_ASSESSOR_BLINDED_RE = re.compile(r"(?:outcome )?assessors? (?:were |was )?blind", re.IGNORECASE)

# A coarse, keyword/field-derived assessment — moderate, not high,
# confidence even when every domain has a real signal.
_ASSESSMENT_CONFIDENCE = 0.6


class RiskOfBiasAssessor(BasePrerequisiteAssessor):
    """See module docstring."""

    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> RiskOfBiasAssessment:
        study_design = classification.study_design.label
        text = document.full_text

        if study_design in _RCT_DESIGNS:
            tool = RiskAssessmentTool.ROB2
            domains = self._rob2_domains(medical, text)
        elif study_design in _OBSERVATIONAL_DESIGNS:
            tool = RiskAssessmentTool.NEWCASTLE_OTTAWA
            domains = self._newcastle_ottawa_domains(medical, text)
        else:
            tool = RiskAssessmentTool.UNKNOWN
            domains = {}

        overall_risk = self._overall_risk(domains)
        downgrade_level = 2 if self._high_risk_domain_count(domains) >= 2 else (1 if overall_risk == RiskLevel.HIGH else 0)

        return RiskOfBiasAssessment(
            overall_risk=overall_risk,
            domains=domains,
            assessment_tool=tool,
            sources=[f"{bias_type.value}: {domain.support_text}" for bias_type, domain in domains.items()],
            confidence=_ASSESSMENT_CONFIDENCE if domains else 0.0,
            evidence=[domain.evidence for domain in domains.values() if domain.evidence is not None],
            downgrade_recommendation=downgrade_level > 0,
            downgrade_level=downgrade_level,
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 50

    # ------------------------------------------------------------ RoB2 (RCTs)

    def _rob2_domains(self, medical: MedicalUnderstanding, text: str) -> dict[BiasType, RiskDomain]:
        domains: dict[BiasType, RiskDomain] = {}

        randomization_method = medical.study_characteristics.randomization_method if medical.study_characteristics else None
        domains[BiasType.RANDOMIZATION] = (
            RiskDomain(RiskLevel.LOW, "randomization method described in study characteristics")
            if randomization_method
            else RiskDomain(RiskLevel.UNCLEAR, "no randomization method described")
        )

        blinding = medical.study_characteristics.blinding if medical.study_characteristics else None
        domains[BiasType.DEVIATIONS_FROM_INTERVENTION] = self._blinding_domain(blinding)

        domains[BiasType.MISSING_OUTCOME_DATA] = (
            RiskDomain(RiskLevel.LOW, "intention-to-treat analysis reported")
            if _ITT_RE.search(text)
            else RiskDomain(RiskLevel.UNCLEAR, "no intention-to-treat analysis mentioned")
        )

        domains[BiasType.OUTCOME_MEASUREMENT] = (
            RiskDomain(RiskLevel.LOW, "outcome assessors reported as blinded")
            if _ASSESSOR_BLINDED_RE.search(text)
            else self._blinding_domain(blinding)
        )

        domains[BiasType.SELECTIVE_REPORTING] = (
            RiskDomain(RiskLevel.LOW, "trial registration reported")
            if _REGISTRATION_RE.search(text)
            else RiskDomain(RiskLevel.UNCLEAR, "no trial registration mentioned")
        )

        return domains

    @staticmethod
    def _blinding_domain(blinding: str) -> RiskDomain:
        if not blinding:
            return RiskDomain(RiskLevel.UNCLEAR, "no blinding method described")
        lowered = blinding.lower()
        if "double" in lowered or "triple" in lowered:
            return RiskDomain(RiskLevel.LOW, f"blinding reported: {blinding}")
        if "single" in lowered:
            return RiskDomain(RiskLevel.MODERATE, f"blinding reported: {blinding}")
        if "open" in lowered:
            return RiskDomain(RiskLevel.HIGH, f"open-label design: {blinding}")
        return RiskDomain(RiskLevel.UNCLEAR, f"blinding reported but unclear: {blinding}")

    # ------------------------------------------------------------ Newcastle-Ottawa (observational)

    def _newcastle_ottawa_domains(self, medical: MedicalUnderstanding, text: str) -> dict[BiasType, RiskDomain]:
        domains: dict[BiasType, RiskDomain] = {}

        population = medical.populations[0] if medical.populations else None
        has_criteria = bool(population and (population.inclusion_criteria or population.exclusion_criteria))
        domains[BiasType.SELECTION] = (
            RiskDomain(RiskLevel.LOW, "inclusion/exclusion criteria described")
            if has_criteria
            else RiskDomain(RiskLevel.UNCLEAR, "no inclusion/exclusion criteria described")
        )

        has_comparator = bool(medical.comparators)
        domains[BiasType.COMPARABILITY] = (
            RiskDomain(RiskLevel.LOW, "a comparator group is described")
            if has_comparator
            else RiskDomain(RiskLevel.UNCLEAR, "no comparator group described")
        )

        domains[BiasType.MISSING_OUTCOME_DATA] = (
            RiskDomain(RiskLevel.LOW, "intention-to-treat or equivalent follow-up analysis reported")
            if _ITT_RE.search(text)
            else RiskDomain(RiskLevel.UNCLEAR, "no follow-up completeness analysis mentioned")
        )

        return domains

    @staticmethod
    def _overall_risk(domains: dict[BiasType, RiskDomain]) -> RiskLevel:
        if not domains:
            return RiskLevel.UNKNOWN
        levels = [domain.risk_level for domain in domains.values()]
        if RiskLevel.HIGH in levels:
            return RiskLevel.HIGH
        if all(level == RiskLevel.LOW for level in levels):
            return RiskLevel.LOW
        if RiskLevel.UNCLEAR in levels:
            return RiskLevel.UNCLEAR
        return RiskLevel.MODERATE

    @staticmethod
    def _high_risk_domain_count(domains: dict[BiasType, RiskDomain]) -> int:
        return sum(1 for domain in domains.values() if domain.risk_level == RiskLevel.HIGH)
