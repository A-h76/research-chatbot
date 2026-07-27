"""Dataclasses for the Evidence Grading Engine.

The task gave complete field-level detail for most models here
(Grade, GradeRationale, RiskOfBiasAssessment, ConsistencyAssessment,
PrecisionAssessment, DirectnessAssessment, PublicationBiasAssessment,
ReportingQualityAssessment, GRADEFrameworkResult, AggregationLog,
AuditTrail, AuditDecision, PrerequisiteAssessments, EvidenceGrades) —
those are implemented here exactly as specified, with one addition each
where noted below. The following are referenced throughout the task's
own spec but never defined anywhere in it, and are designed here:

- RiskDomain (dict value type for RiskOfBiasAssessment.domains)
- EffectSize, ConfidenceInterval (PrecisionAssessment's own fields)
- ApplicabilityAssessment (PrerequisiteAssessments.applicability, and
  assessments/applicability.py in the directory tree — no field spec
  anywhere; designed as a light, honestly-scoped generalizability
  assessment distinct from DirectnessAssessment's narrower PICO-matching)
- FrameworkResult (BaseFrameworkGrader.grade()'s return type — a generic
  envelope so aggregators/pipeline.py consume all four frameworks
  uniformly; GRADEFrameworkResult is GRADE's own richer payload, carried
  inside FrameworkResult.grade_result for that one framework only)
- OutcomeGrade (EvidenceGrades.outcome_grades' dict value type)
- ConflictResolution (AggregationLog.conflict_resolution_log's item type)
- PrerequisiteAssessment (singular — BasePrerequisiteAssessor.assess()'s
  return type; a Union of the seven concrete assessment dataclasses,
  distinct from the given PLURAL PrerequisiteAssessments shared-cache
  dataclass)
- ConfidenceScore, ExtractionError, RecoveryAction — this phase's own
  local definitions (not a reuse of backend.medical_understanding's
  identically-named classes) — see enums.py's own module docstring for
  why each phase keeps an independent definition of these supporting
  concepts.

One addition to EvidenceGrades beyond its given field list: skipped/
reasoning. The task's own framing ("Critical: ... It runs only when the
AnalysisContext routing profile indicates evidence grading is required")
is identical in spirit to Phase 1.4's, which modeled exactly this as
skipped/reasoning on MedicalUnderstanding — but the EvidenceGrades shape
given here has no field capable of representing "this didn't run" at
all. Added for the same reason, with every other field defaulting to an
empty/neutral value so `EvidenceGrades(skipped=True, reasoning=...)`
works standalone, mirroring MedicalUnderstanding's identical pattern.

Every assessment/result dataclass here is evidence-linked via
backend.document_understanding.models.EvidenceReference (Phase 1.1) —
same discipline every phase since 1.1 has followed.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union

from backend.classification.pass2.enums import ReportingGuideline
from backend.document_understanding.models import EvidenceReference
from backend.medical_understanding.enums import StatisticalMeasureType

from .enums import (
    AggregationStrategy,
    BiasType,
    ConsistencyLevel,
    DirectnessLevel,
    ErrorSeverity,
    ErrorType,
    GradeType,
    GradingFramework,
    GRADEDowngradeFactor,
    GRADEQuality,
    GRADEUpgradeFactor,
    PrecisionLevel,
    RecommendationStrength,
    RecoveryType,
    RiskAssessmentTool,
    RiskLevel,
    StudyQuality,
)

# ------------------------------------------------------------ this phase's own confidence model
#
# Defined early (before anything that references it, e.g.
# PrerequisiteAssessments.confidence below) since dataclass __init__ is
# generated at class-body execution time — a field default referencing a
# not-yet-defined name can't be patched in after the fact.


@dataclass
class ConfidenceScore:
    """Deterministic, explainable confidence — matches config.py's own
    confidence_formula string exactly."""

    overall: float
    components: dict[str, float]
    formula: str

    @staticmethod
    def calculate(
        evidence_support: float,
        framework_completeness: float,
        assessment_agreement: float,
        extraction_confidence: float,
    ) -> "ConfidenceScore":
        overall = (
            0.35 * evidence_support
            + 0.25 * framework_completeness
            + 0.20 * assessment_agreement
            + 0.20 * extraction_confidence
        )
        return ConfidenceScore(
            overall=min(1.0, max(0.0, overall)),
            components={
                "evidence_support": evidence_support,
                "framework_completeness": framework_completeness,
                "assessment_agreement": assessment_agreement,
                "extraction_confidence": extraction_confidence,
            },
            formula=(
                "0.35*evidence_support + 0.25*framework_completeness + "
                "0.20*assessment_agreement + 0.20*extraction_confidence"
            ),
        )

    @staticmethod
    def empty() -> "ConfidenceScore":
        return ConfidenceScore(overall=0.0, components={}, formula="")


# ------------------------------------------------------------ small gap-filled leaves


@dataclass
class RiskDomain:
    """One bias domain's own rating within a RiskOfBiasAssessment — see
    models.py's own module docstring."""

    risk_level: RiskLevel = RiskLevel.UNKNOWN
    support_text: str = ""
    evidence: Optional[EvidenceReference] = None


@dataclass
class EffectSize:
    """One reported effect-size measure feeding PrecisionAssessment (and,
    via GRADEUpgradeFactor.LARGE_EFFECT, frameworks/grade.py's upgrade
    logic). measure_type reuses backend.medical_understanding's own
    StatisticalMeasureType (Phase 1.4) rather than a new enum — this
    value is directly derived from MedicalUnderstanding.
    statistical_measures, so reusing the same type is the non-duplicative
    choice (distinct from ConfidenceScore/ErrorType, which are purely
    internal bookkeeping with no cross-phase data-flow requirement)."""

    measure_type: StatisticalMeasureType = StatisticalMeasureType.OTHER
    value: float = 0.0
    is_large_effect: bool = False


@dataclass
class ConfidenceInterval:
    lower: float = 0.0
    upper: float = 0.0
    level: float = 0.95


# ------------------------------------------------------------ given verbatim by the task


@dataclass
class GradeRationale:
    """Structured rationale for traceability."""

    rule_applied: str
    evidence_used: list[EvidenceReference]
    confidence_impact: float
    framework_source: str
    reasoning: str


@dataclass
class Grade:
    grade_type: GradeType = GradeType.EVIDENCE_QUALITY
    grade_value: str = ""
    grade_description: str = ""
    confidence: float = 0.0
    framework: GradingFramework = GradingFramework.UNKNOWN
    prerequisites_used: list[str] = field(default_factory=list)
    rationale: list[GradeRationale] = field(default_factory=list)
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class RiskOfBiasAssessment:
    overall_risk: RiskLevel = RiskLevel.UNKNOWN
    domains: dict[BiasType, RiskDomain] = field(default_factory=dict)
    assessment_tool: RiskAssessmentTool = RiskAssessmentTool.UNKNOWN
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)
    downgrade_recommendation: bool = False
    downgrade_level: int = 0


@dataclass
class ConsistencyAssessment:
    consistency_score: float = 0.0
    consistency_level: ConsistencyLevel = ConsistencyLevel.UNKNOWN
    heterogeneity: Optional[float] = None  # I² statistic
    p_value: Optional[float] = None  # Q-test p-value
    findings: list[str] = field(default_factory=list)
    applicable: bool = False
    downgrade_recommendation: bool = False
    downgrade_level: int = 0
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class PrecisionAssessment:
    precision_score: float = 0.0
    precision_level: PrecisionLevel = PrecisionLevel.UNKNOWN
    effect_size: Optional[EffectSize] = None
    confidence_interval: Optional[ConfidenceInterval] = None
    sample_size: Optional[int] = None
    downgrade_recommendation: bool = False
    downgrade_level: int = 0
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class DirectnessAssessment:
    directness_score: float = 0.0
    directness_level: DirectnessLevel = DirectnessLevel.UNKNOWN
    population_match: float = 0.0
    intervention_match: float = 0.0
    comparator_match: float = 0.0
    outcome_match: float = 0.0
    downgrade_recommendation: bool = False
    downgrade_level: int = 0
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class PublicationBiasAssessment:
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    applicable: bool = False
    funnel_plot_asymmetry: Optional[bool] = None
    small_study_effects: Optional[bool] = None
    downgrade_recommendation: bool = False
    downgrade_level: int = 0
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class ReportingQualityAssessment:
    """Separate from evidence quality — see package docstring's Design
    Decision 3. reporting_guideline reuses backend.classification.pass2's
    own ReportingGuideline enum (Phase 1.2)."""

    reporting_quality_score: float = 0.0  # 0-100
    reporting_guideline: ReportingGuideline = ReportingGuideline.UNKNOWN
    compliance_items: dict[str, bool] = field(default_factory=dict)
    missing_items: list[str] = field(default_factory=list)
    partially_met_items: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class GRADEFrameworkResult:
    evidence_quality: GRADEQuality = GRADEQuality.VERY_LOW
    recommendation_strength: Optional[RecommendationStrength] = None
    downgrade_factors: list[GRADEDowngradeFactor] = field(default_factory=list)
    upgrade_factors: list[GRADEUpgradeFactor] = field(default_factory=list)
    initial_quality: GRADEQuality = GRADEQuality.VERY_LOW
    final_quality: GRADEQuality = GRADEQuality.VERY_LOW
    rationale: list[GradeRationale] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class AuditDecision:
    decision_id: str
    rule: str
    evidence: list[EvidenceReference]
    framework: GradingFramework
    confidence_before: float
    confidence_after: float
    confidence_delta: float
    result: str
    reasoning: str
    timestamp: datetime


@dataclass
class AuditTrail:
    """Complete audit trail for every grading decision."""

    decisions: list[AuditDecision] = field(default_factory=list)

    def add_decision(
        self,
        decision_id: str,
        rule: str,
        evidence: list[EvidenceReference],
        framework: GradingFramework,
        confidence_delta: float,
        result: str,
    ) -> None:
        """The task's own add_decision() signature omits confidence_before/
        confidence_after/reasoning that AuditDecision itself requires —
        reconciled here by deriving them: confidence_before is the
        running total from the last-recorded decision (0.0 if this is
        the first), confidence_after = confidence_before + delta, and
        reasoning is a plain sentence built from rule/result (a caller
        wanting a richer reasoning string constructs an AuditDecision
        directly and appends it instead)."""
        confidence_before = self.decisions[-1].confidence_after if self.decisions else 0.0
        confidence_after = confidence_before + confidence_delta
        self.decisions.append(
            AuditDecision(
                decision_id=decision_id,
                rule=rule,
                evidence=evidence,
                framework=framework,
                confidence_before=confidence_before,
                confidence_after=confidence_after,
                confidence_delta=confidence_delta,
                result=result,
                reasoning=f"{rule} -> {result}",
                timestamp=datetime.now(timezone.utc),
            )
        )


# ------------------------------------------------------------ this module's own gap-fills (larger)


@dataclass
class ApplicabilityAssessment:
    """How generalizable this evidence is to real-world clinical practice
    beyond the exact PICO match DirectnessAssessment already captures
    (population/intervention/comparator/outcome matching) — broader
    setting/context generalizability concerns. No field-level spec was
    given anywhere in the task for this model (see module docstring) —
    designed here as a light, honestly-scoped assessment."""

    applicability_score: float = 0.0
    setting_generalizability: float = 0.0
    population_generalizability: float = 0.0
    concerns: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class FrameworkResult:
    """Generic envelope every BaseFrameworkGrader.grade() call returns —
    the framework's own Grade, plus (GRADE only) its richer
    GRADEFrameworkResult payload in grade_result. Aggregators/pipeline.py
    consume `grade` uniformly across all four frameworks, so a future
    fifth framework never requires aggregator changes."""

    framework: GradingFramework = GradingFramework.UNKNOWN
    grade: Grade = field(default_factory=Grade)
    grade_result: Optional[GRADEFrameworkResult] = None
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class OutcomeGrade:
    """One outcome's own grade — see aggregators/outcome_aggregator.py."""

    outcome_name: str = ""
    grade: Grade = field(default_factory=Grade)
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class ConflictResolution:
    """One detected disagreement between two frameworks' grades and how
    it was resolved — see aggregators/conflict_resolver.py."""

    frameworks_involved: list[GradingFramework] = field(default_factory=list)
    conflicting_values: dict[str, str] = field(default_factory=dict)
    resolution_strategy: str = ""
    resolved_value: str = ""
    reasoning: str = ""


@dataclass
class AggregationLog:
    """Complete record of aggregation decisions."""

    inputs: dict[str, Grade] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    aggregation_strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_AVERAGE
    conflict_resolution_log: list[ConflictResolution] = field(default_factory=list)
    final_grade: Grade = field(default_factory=Grade)
    confidence_delta: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PrerequisiteAssessments:
    """Shared assessments consumed by multiple frameworks — built once
    per pipeline run, never recomputed per-framework (see package
    docstring's Design Decision 1)."""

    risk_of_bias: RiskOfBiasAssessment = field(default_factory=RiskOfBiasAssessment)
    consistency: ConsistencyAssessment = field(default_factory=ConsistencyAssessment)
    precision: PrecisionAssessment = field(default_factory=PrecisionAssessment)
    directness: DirectnessAssessment = field(default_factory=DirectnessAssessment)
    publication_bias: Optional[PublicationBiasAssessment] = None
    reporting_quality: ReportingQualityAssessment = field(default_factory=ReportingQualityAssessment)
    applicability: ApplicabilityAssessment = field(default_factory=ApplicabilityAssessment)

    confidence: ConfidenceScore = field(default_factory=ConfidenceScore.empty)
    evidence: list[EvidenceReference] = field(default_factory=list)


# BasePrerequisiteAssessor.assess()'s return type — a Union of the seven
# concrete assessments, distinct from the plural PrerequisiteAssessments
# shared-cache dataclass above (see module docstring).
PrerequisiteAssessment = Union[
    RiskOfBiasAssessment,
    ConsistencyAssessment,
    PrecisionAssessment,
    DirectnessAssessment,
    PublicationBiasAssessment,
    ReportingQualityAssessment,
    ApplicabilityAssessment,
]


# ------------------------------------------------------------ this phase's own error models


@dataclass
class RecoveryAction:
    action_type: RecoveryType
    description: str
    success: bool
    fallback_value: Any = None


@dataclass
class ExtractionError:
    """component names whichever assessor/framework/aggregator failed —
    renamed from Phase 1.4's identically-shaped "extractor" field since
    not every failure here comes from an extractor-shaped component."""

    component: str
    error_type: ErrorType
    message: str
    severity: ErrorSeverity
    recovery_attempted: bool = False
    recovered: bool = False
    recovery_action: Optional[RecoveryAction] = None


# ------------------------------------------------------------ the top-level container


@dataclass
class EvidenceGrades:
    """EvidenceGradingPipeline's final output — see package docstring's
    note on the added skipped/reasoning fields (not in the task's own
    given field list) and pipeline.py's own module docstring for the
    full stage diagram.

    Every field beyond skipped/reasoning defaults to an empty/neutral
    value so the `skipped=True` fast path (evidence grading not required
    for this document) can construct one with just those two kwargs,
    mirroring MedicalUnderstanding's identical pattern."""

    skipped: bool = False
    reasoning: Optional[str] = None
    overall_grade: Grade = field(default_factory=Grade)
    study_quality: StudyQuality = StudyQuality.UNKNOWN
    risk_of_bias: RiskOfBiasAssessment = field(default_factory=RiskOfBiasAssessment)
    consistency: ConsistencyAssessment = field(default_factory=ConsistencyAssessment)
    precision: PrecisionAssessment = field(default_factory=PrecisionAssessment)
    directness: DirectnessAssessment = field(default_factory=DirectnessAssessment)
    publication_bias: Optional[PublicationBiasAssessment] = None
    reporting_quality: ReportingQualityAssessment = field(default_factory=ReportingQualityAssessment)
    outcome_grades: dict[str, OutcomeGrade] = field(default_factory=dict)
    framework_results: dict[GradingFramework, FrameworkResult] = field(default_factory=dict)
    aggregation_log: AggregationLog = field(default_factory=AggregationLog)
    audit_trail: AuditTrail = field(default_factory=AuditTrail)
    confidence: ConfidenceScore = field(default_factory=ConfidenceScore.empty)
    warnings: list[str] = field(default_factory=list)
    errors: list[ExtractionError] = field(default_factory=list)
    processing_time_ms: float = 0.0
    pipeline_version: str = ""
