"""Configuration for the Evidence Grading Engine. Every tunable
referenced elsewhere in this package lives here, not as a scattered
magic number in the module that actually uses it.

One documented deviation from the task's own literal default:
plugin_allowlist defaults to an empty list, but security/isolation.py
treats an EMPTY allowlist as "unrestricted" rather than "deny everything"
— read literally, an empty allowlist would reject every one of this
pipeline's own default-registered assessors/graders/aggregators on a
fresh EvidenceGradingConfig(), breaking the pipeline out of the box.
Populating plugin_allowlist with specific names is what actually turns
on the restriction; see security/isolation.py's own module docstring.
"""

from dataclasses import dataclass, field
from typing import Optional

from .enums import AggregationStrategy, GradingFramework, GRADEQuality


@dataclass
class EvidenceGradingConfig:
    """See module docstring. Field names/defaults otherwise match the
    originating task's own configuration spec verbatim."""

    # Enabled frameworks
    enabled_frameworks: list[GradingFramework] = field(
        default_factory=lambda: [GradingFramework.GRADE, GradingFramework.OXFORD]
    )

    # Assessment enablement
    enable_risk_of_bias: bool = True
    enable_consistency: bool = True
    enable_precision: bool = True
    enable_directness: bool = True
    enable_publication_bias: bool = True
    enable_reporting_quality: bool = True

    # Applicability rules
    publication_bias_only_reviews: bool = True
    consistency_only_reviews: bool = True

    # GRADE specific — keyed by backend.classification.pass2.enums.
    # StudyDesign's own string values ("rct", "systematic_review", ...),
    # matching the task's own example verbatim.
    grade_initial_quality_mapping: dict[str, GRADEQuality] = field(
        default_factory=lambda: {
            "rct": GRADEQuality.HIGH,
            "observational": GRADEQuality.LOW,
            "systematic_review": GRADEQuality.HIGH,
        }
    )

    # Aggregation
    aggregation_strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_AVERAGE
    framework_weights: dict[GradingFramework, float] = field(
        default_factory=lambda: {GradingFramework.GRADE: 0.6, GradingFramework.OXFORD: 0.4}
    )
    conflict_resolution_strategy: str = "majority"  # "majority", "conservative", "liberal"

    # Confidence formula
    confidence_formula: str = (
        "0.35*evidence_support + 0.25*framework_completeness + "
        "0.20*assessment_agreement + 0.20*extraction_confidence"
    )

    # Security
    max_outcomes: int = 100
    max_bias_domains: int = 20
    max_rationale_strings: int = 500
    max_rationale_length: int = 1000
    max_evidence_references: int = 1000
    max_processing_time_ms: int = 30000
    plugin_timeout_ms: int = 5000

    # Audit
    enable_audit_trail: bool = True
    audit_trail_verbosity: str = "detailed"

    # Parallel execution
    enable_parallel: bool = True
    max_parallel_workers: int = 4

    # Cache
    cache_enabled: bool = True
    cache_size: int = 100

    # Determinism
    deterministic_seed: Optional[int] = None

    # Retry
    retry_policy: str = "backoff"
    max_retries: int = 3

    # Plugin isolation — see module docstring for the empty-allowlist
    # semantics.
    plugin_allowlist: list[str] = field(default_factory=list)
    plugin_sandbox_enabled: bool = True
