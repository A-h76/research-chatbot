"""Final cross-framework grade aggregation — combines every enabled
framework's own Grade into one AggregationLog.final_grade per
config.aggregation_strategy. Runs after conflict_resolver.detect_and_
resolve() (pipeline step 4, this module's step 5), and always logs
whatever conflict was found, but only actually USES the conflict-
resolution outcome when aggregation_strategy is CONSENSUS — the other
four strategies (WEIGHTED_AVERAGE, MINIMUM, PRIORITY, RANKED) compute
their own result directly from each framework's normalized position,
independent of conflict_resolution_strategy.
"""

from ..config import EvidenceGradingConfig
from ..enums import AggregationStrategy, GradeType, GradingFramework
from ..models import AggregationLog, FrameworkResult, Grade, GradeRationale
from .conflict_resolver import bucket_label, detect_and_resolve, normalize_grade


def aggregate_grade(
    framework_results: dict[GradingFramework, FrameworkResult],
    config: EvidenceGradingConfig,
) -> AggregationLog:
    if not framework_results:
        return AggregationLog(
            aggregation_strategy=config.aggregation_strategy,
            final_grade=Grade(grade_type=GradeType.AGGREGATE, grade_value="unknown"),
        )

    conflict, resolved_position = detect_and_resolve(framework_results, config)
    positions = {fw: normalize_grade(fw, result.grade.grade_value) for fw, result in framework_results.items()}
    mean_position = sum(positions.values()) / len(positions)

    final_position = _aggregate_by_strategy(positions, config, resolved_position)
    final_label = bucket_label(final_position)

    confidence = sum(result.confidence for result in framework_results.values()) / len(framework_results)
    evidence = [reference for result in framework_results.values() for reference in result.evidence]

    rationale = [
        GradeRationale(
            rule_applied=config.aggregation_strategy.value,
            evidence_used=evidence,
            confidence_impact=0.0,
            framework_source="aggregation",
            reasoning=f"combined {len(framework_results)} framework(s) via {config.aggregation_strategy.value} -> {final_label}",
        )
    ]

    final_grade = Grade(
        grade_type=GradeType.AGGREGATE,
        grade_value=final_label,
        grade_description=f"Aggregated evidence quality ({config.aggregation_strategy.value}): {final_label}",
        confidence=confidence,
        framework=GradingFramework.UNKNOWN,
        prerequisites_used=[],
        rationale=rationale,
        evidence=evidence,
    )

    return AggregationLog(
        inputs={fw.value: result.grade for fw, result in framework_results.items()},
        weights={fw.value: config.framework_weights.get(fw, 1.0) for fw in framework_results},
        aggregation_strategy=config.aggregation_strategy,
        conflict_resolution_log=[conflict] if conflict else [],
        final_grade=final_grade,
        confidence_delta=final_position - mean_position,
    )


def _aggregate_by_strategy(
    positions: dict[GradingFramework, float],
    config: EvidenceGradingConfig,
    resolved_position: float,
) -> float:
    strategy = config.aggregation_strategy

    if strategy == AggregationStrategy.MINIMUM:
        return min(positions.values())

    if strategy == AggregationStrategy.PRIORITY:
        best_framework = max(positions, key=lambda fw: config.framework_weights.get(fw, 0.0))
        return positions[best_framework]

    if strategy == AggregationStrategy.RANKED:
        ranked = sorted(positions, key=lambda fw: config.framework_weights.get(fw, 0.0), reverse=True)
        rank_weights = {fw: 1.0 / (i + 1) for i, fw in enumerate(ranked)}
        total_weight = sum(rank_weights.values())
        return sum(positions[fw] * rank_weights[fw] for fw in ranked) / total_weight

    if strategy == AggregationStrategy.CONSENSUS:
        return resolved_position

    # WEIGHTED_AVERAGE (default)
    weights = {fw: config.framework_weights.get(fw, 1.0) for fw in positions}
    total_weight = sum(weights.values())
    if total_weight == 0:
        return sum(positions.values()) / len(positions)
    return sum(positions[fw] * weights[fw] for fw in positions) / total_weight
