"""Audit trail generation — thin, reusable helpers every framework/
aggregator uses to record a decision consistently onto one shared
AuditTrail instance, rather than each caller hand-building an
AuditDecision (models.py's AuditTrail.add_decision() already handles the
underlying confidence-tracking arithmetic — see its own docstring for
why its signature omits confidence_before/confidence_after/reasoning and
how those get derived).

Downgrade/upgrade confidence deltas are a small, fixed, documented
constant per level (not derived from any real statistical weighting the
task specified) — the audit trail's job is complete traceability of
*what* decision was made and *why*, not a precise confidence-impact
model; frameworks/grade.py's own GRADEFrameworkResult.confidence is the
actual grading-confidence signal, unaffected by this module's numbers.
"""

from backend.document_understanding.models import EvidenceReference

from .enums import GradingFramework
from .models import AuditTrail

# Per-level confidence impact recorded for a downgrade/upgrade decision —
# see module docstring on why this is a fixed constant, not derived.
_DOWNGRADE_CONFIDENCE_DELTA_PER_LEVEL = -0.1
_UPGRADE_CONFIDENCE_DELTA_PER_LEVEL = 0.1


def record_downgrade(
    trail: AuditTrail,
    framework: GradingFramework,
    factor: str,
    levels: int,
    evidence: list[EvidenceReference],
) -> None:
    trail.add_decision(
        decision_id=f"{framework.value}:downgrade:{factor}",
        rule=f"downgrade for {factor}",
        evidence=evidence,
        framework=framework,
        confidence_delta=_DOWNGRADE_CONFIDENCE_DELTA_PER_LEVEL * levels,
        result=f"downgraded by {levels} level(s)",
    )


def record_upgrade(
    trail: AuditTrail,
    framework: GradingFramework,
    factor: str,
    levels: int,
    evidence: list[EvidenceReference],
) -> None:
    trail.add_decision(
        decision_id=f"{framework.value}:upgrade:{factor}",
        rule=f"upgrade for {factor}",
        evidence=evidence,
        framework=framework,
        confidence_delta=_UPGRADE_CONFIDENCE_DELTA_PER_LEVEL * levels,
        result=f"upgraded by {levels} level(s)",
    )


def record_aggregation(
    trail: AuditTrail,
    strategy: str,
    result: str,
    evidence: list[EvidenceReference],
) -> None:
    trail.add_decision(
        decision_id=f"aggregation:{strategy}",
        rule=f"aggregation strategy: {strategy}",
        evidence=evidence,
        framework=GradingFramework.UNKNOWN,
        confidence_delta=0.0,
        result=result,
    )


def record_conflict_resolution(
    trail: AuditTrail,
    resolution_strategy: str,
    resolved_value: str,
    evidence: list[EvidenceReference],
) -> None:
    trail.add_decision(
        decision_id=f"conflict_resolution:{resolution_strategy}",
        rule=f"conflict resolution strategy: {resolution_strategy}",
        evidence=evidence,
        framework=GradingFramework.UNKNOWN,
        confidence_delta=0.0,
        result=f"resolved to {resolved_value!r}",
    )
