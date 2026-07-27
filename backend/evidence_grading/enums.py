"""Closed label sets for the Evidence Grading Engine.

Given verbatim by the task: RiskAssessmentTool, ConsistencyLevel,
PrecisionLevel, DirectnessLevel, AggregationStrategy, GRADEDowngradeFactor,
GRADEUpgradeFactor.

Everything else here is a gap-fill: GradingFramework itself is used in
nearly every signature in the task's own spec (Grade.framework, config.
enabled_frameworks, BaseFrameworkGrader.framework(), ...) but never
defined; GradeType/StudyQuality/RiskLevel/BiasType/GRADEQuality/
RecommendationStrength are each referenced by a model field the task
gives in full but likewise never defined. All are designed here using
real, standard terminology from the actual frameworks named (Cochrane
RoB2's five domains, GRADE's four-level HIGH/MODERATE/LOW/VERY_LOW
scale, ...), not invented ad hoc — see models.py's own module docstring
for the parallel gap-fill list of dataclasses.

USPSTF appears in the task's own directory tree (frameworks/usptf.py)
but nowhere else — not in Implementation Order, not in Completion
Criteria, not in the default config.enabled_frameworks example — the
same "listed once, never followed up" pattern seen in every prior
phase's own plan gaps. GradingFramework has no USPSTF member; see
package docstring for the same decision applied to frameworks/usptf.py
itself (not built).
"""

from enum import Enum

# ------------------------------------------------------------ given verbatim by the task


class RiskAssessmentTool(str, Enum):
    ROB2 = "rob2"  # Cochrane Risk of Bias 2.0
    NEWCASTLE_OTTAWA = "newcastle_ottawa"
    QUADAS2 = "quadas2"
    PROBAST = "probast"
    NIH = "nih"
    SIGN = "sign"
    UNKNOWN = "unknown"


class ConsistencyLevel(str, Enum):
    HIGHLY_CONSISTENT = "highly_consistent"
    MODERATELY_CONSISTENT = "moderately_consistent"
    INCONSISTENT = "inconsistent"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class PrecisionLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class DirectnessLevel(str, Enum):
    DIRECT = "direct"
    MODERATELY_DIRECT = "moderately_direct"
    INDIRECT = "indirect"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class AggregationStrategy(str, Enum):
    WEIGHTED_AVERAGE = "weighted_average"
    MINIMUM = "minimum"
    PRIORITY = "priority"
    CONSENSUS = "consensus"
    RANKED = "ranked"


class GRADEDowngradeFactor(str, Enum):
    RISK_OF_BIAS = "risk_of_bias"
    INCONSISTENCY = "inconsistency"
    INDIRECTNESS = "indirectness"
    IMPRECISION = "imprecision"
    PUBLICATION_BIAS = "publication_bias"


class GRADEUpgradeFactor(str, Enum):
    LARGE_EFFECT = "large_effect"
    DOSE_RESPONSE = "dose_response"
    RESIDUAL_CONFOUNDING = "residual_confounding"


# ------------------------------------------------------------ this module's own gap-fills


class GradingFramework(str, Enum):
    """See module docstring — referenced constantly, never defined. No
    USPSTF member — see module docstring."""

    GRADE = "grade"
    OXFORD = "oxford"
    NIH = "nih"
    SIGN = "sign"
    UNKNOWN = "unknown"


class GradeType(str, Enum):
    """What kind of grade a Grade instance represents — a single framework's
    own evidence-quality determination, a recommendation strength, the
    final cross-framework aggregate, or a grade scoped to one outcome."""

    EVIDENCE_QUALITY = "evidence_quality"
    RECOMMENDATION_STRENGTH = "recommendation_strength"
    AGGREGATE = "aggregate"
    OUTCOME_SPECIFIC = "outcome_specific"


class StudyQuality(str, Enum):
    """Overall descriptive quality bucket — mirrors GRADE's own four-
    level scale (GRADEQuality below), used for EvidenceGrades.
    study_quality as a framework-agnostic summary independent of which
    specific framework(s) ran."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Standard Cochrane risk-of-bias terminology."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNCLEAR = "unclear"
    UNKNOWN = "unknown"


class BiasType(str, Enum):
    """Bias domains, unified across the two named tools this phase
    supports: Cochrane RoB2's five domains (RANDOMIZATION through
    SELECTIVE_REPORTING) plus Newcastle-Ottawa Scale's three categories
    (SELECTION, COMPARABILITY, folded into the RoB2-shaped
    MISSING_OUTCOME_DATA for its "outcome/exposure ascertainment"
    category) — see assessments/risk_of_bias.py for which tool populates
    which subset."""

    RANDOMIZATION = "randomization"
    DEVIATIONS_FROM_INTERVENTION = "deviations_from_intervention"
    MISSING_OUTCOME_DATA = "missing_outcome_data"
    OUTCOME_MEASUREMENT = "outcome_measurement"
    SELECTIVE_REPORTING = "selective_reporting"
    SELECTION = "selection"
    COMPARABILITY = "comparability"
    OTHER = "other"


class GRADEQuality(str, Enum):
    """The standard four-level GRADE evidence-quality scale."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


class RecommendationStrength(str, Enum):
    """GRADE's own two-level recommendation-strength scale (sometimes
    called "conditional" instead of "weak" in GRADE's own literature;
    STRONG/WEAK are its canonical terms)."""

    STRONG = "strong"
    WEAK = "weak"


# ------------------------------------------------------------ error/recovery taxonomy
#
# Phase 1.5's own local ErrorType/ErrorSeverity/RecoveryType — not a
# reuse of backend.medical_understanding's identically-named enums.
# Every phase so far has kept its own independent definition of same-
# shaped supporting concepts (e.g. ConfidenceScore is redefined fresh in
# each of Phase 1.3/1.4/1.5, never imported across phases) since each
# phase's own error/recovery taxonomy reflects concerns unique to it —
# here, dependency-graph cycles and plugin-isolation failures that have
# no equivalent in Phase 1.4's regex/normalization/ontology-flavored set.


class ErrorType(str, Enum):
    VALIDATION_ERROR = "validation_error"
    ASSESSMENT_ERROR = "assessment_error"
    FRAMEWORK_ERROR = "framework_error"
    AGGREGATION_ERROR = "aggregation_error"
    DEPENDENCY_ERROR = "dependency_error"  # e.g. a cycle in requires()
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_LIMIT_ERROR = "resource_limit_error"
    SECURITY_ERROR = "security_error"  # e.g. plugin not in allowlist
    CONFIDENCE_ERROR = "confidence_error"


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"  # Pipeline must stop
    ERROR = "error"  # Module failed, can continue
    WARNING = "warning"  # Non-critical issue
    INFO = "info"  # Informational


class RecoveryType(str, Enum):
    FALLBACK_FRAMEWORK = "fallback_framework"
    DEFAULT_ASSESSMENT = "default_assessment"
    SKIP_FRAMEWORK = "skip_framework"
    CONSERVATIVE_GRADE = "conservative_grade"
    RETRY = "retry"
