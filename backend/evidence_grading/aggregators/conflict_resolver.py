"""Cross-framework conflict detection and resolution.

Each framework grades on its own native scale (GRADE's 4-level HIGH/
MODERATE/LOW/VERY_LOW, Oxford's 1-5, NIH's good/fair/poor, SIGN's
1++/../4) — comparing them directly isn't meaningful, so every grade is
first normalized onto a common 0-1 "quality position" (1.0 = best
possible evidence on that framework's own scale, 0.0 = worst), then
compared. A real conflict is a spread (max-min) beyond
_CONFLICT_THRESHOLD; smaller spreads are ordinary cross-framework noise,
not a disagreement worth logging.

This normalization is also the basis for confidence.py's own
assessment_agreement input (agreement_score() below) — computed once
here rather than duplicated in confidence.py, per confidence.py's own
module docstring.
"""

from statistics import pstdev
from typing import Optional

from ..config import EvidenceGradingConfig
from ..enums import GradingFramework
from ..models import ConflictResolution, FrameworkResult

_CONFLICT_THRESHOLD = 0.3

_GRADE_POSITIONS = {"high": 1.0, "moderate": 0.67, "low": 0.33, "very_low": 0.0}
_OXFORD_POSITIONS = {"1": 1.0, "2": 0.75, "3": 0.5, "4": 0.25, "5": 0.0}
_NIH_POSITIONS = {"good": 1.0, "fair": 0.5, "poor": 0.0}
_SIGN_POSITIONS = {
    "1++": 1.0,
    "1+": 0.83,
    "1-": 0.67,
    "2++": 0.67,
    "2+": 0.5,
    "2-": 0.33,
    "3": 0.17,
    "4": 0.0,
}
_POSITIONS_BY_FRAMEWORK = {
    GradingFramework.GRADE: _GRADE_POSITIONS,
    GradingFramework.OXFORD: _OXFORD_POSITIONS,
    GradingFramework.NIH: _NIH_POSITIONS,
    GradingFramework.SIGN: _SIGN_POSITIONS,
}

# The bucket label a resolved cross-framework value is expressed in —
# GRADE's own vocabulary, since it's the most granular common scale.
_BUCKET_LABELS = ["very_low", "low", "moderate", "high"]


def normalize_grade(framework: GradingFramework, grade_value: str) -> float:
    """0.0-1.0 quality position for one framework's own native grade
    value; 0.5 (neutral) if the framework/value isn't recognized."""
    table = _POSITIONS_BY_FRAMEWORK.get(framework, {})
    return table.get(grade_value, 0.5)


def agreement_score(framework_results: dict[GradingFramework, FrameworkResult]) -> float:
    """1.0 = every framework lands on the same quality position, 0.0 =
    maximally spread. A single (or zero) framework trivially agrees with
    itself."""
    positions = [normalize_grade(fw, result.grade.grade_value) for fw, result in framework_results.items()]
    if len(positions) <= 1:
        return 1.0
    return max(0.0, 1.0 - pstdev(positions))


def bucket_label(position: float) -> str:
    if position >= 0.75:
        return "high"
    if position >= 0.5:
        return "moderate"
    if position >= 0.25:
        return "low"
    return "very_low"


def detect_and_resolve(
    framework_results: dict[GradingFramework, FrameworkResult],
    config: EvidenceGradingConfig,
) -> tuple[Optional[ConflictResolution], float]:
    """Returns (conflict_or_None, resolved_normalized_position). No
    ConflictResolution is produced when frameworks already agree
    (spread <= _CONFLICT_THRESHOLD) — the resolved position is then just
    their mean. A real conflict is resolved per config.
    conflict_resolution_strategy ("majority"/"conservative"/"liberal")
    and logged."""
    positions = {fw: normalize_grade(fw, result.grade.grade_value) for fw, result in framework_results.items()}
    if len(positions) <= 1:
        return None, next(iter(positions.values()), 0.0)

    spread = max(positions.values()) - min(positions.values())
    if spread <= _CONFLICT_THRESHOLD:
        return None, sum(positions.values()) / len(positions)

    strategy = config.conflict_resolution_strategy
    resolved_position = _resolve(positions, strategy)

    conflict = ConflictResolution(
        frameworks_involved=list(positions.keys()),
        conflicting_values={fw.value: framework_results[fw].grade.grade_value for fw in positions},
        resolution_strategy=strategy,
        resolved_value=bucket_label(resolved_position),
        reasoning=f"spread {spread:.2f} exceeds threshold {_CONFLICT_THRESHOLD} -> resolved via '{strategy}'",
    )
    return conflict, resolved_position


def _resolve(positions: dict[GradingFramework, float], strategy: str) -> float:
    if strategy == "conservative":
        return min(positions.values())
    if strategy == "liberal":
        return max(positions.values())
    # "majority": bucket every position, take the most common bucket's mean position;
    # ties broken conservatively (lowest bucket among the tied ones).
    buckets: dict[str, list[float]] = {}
    for position in positions.values():
        buckets.setdefault(bucket_label(position), []).append(position)
    winning = max(buckets.items(), key=lambda item: (len(item[1]), -_BUCKET_LABELS.index(item[0])))
    return sum(winning[1]) / len(winning[1])
