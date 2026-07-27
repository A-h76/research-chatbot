"""Confidence-based component filtering — CRITICAL components always pass."""

from ..config import PromptAssemblyConfig
from ..enums import PromptPriority
from ..models import ConfidenceFilterResult, PromptComponent


def filter_by_confidence(
    components: list[PromptComponent],
    config: PromptAssemblyConfig,
) -> tuple[list[PromptComponent], ConfidenceFilterResult]:
    critical_types = set(config.critical_component_types)
    included: list[PromptComponent] = []
    included_names: list[str] = []
    excluded_names: list[str] = []

    for component in components:
        is_critical = (
            component.priority_level == PromptPriority.CRITICAL
            or component.component_type.value in critical_types
        )
        if is_critical or component.confidence >= config.confidence_threshold:
            included.append(component)
            included_names.append(component.component_type.value)
        else:
            excluded_names.append(component.component_type.value)

    result = ConfidenceFilterResult(
        threshold=config.confidence_threshold,
        included_items=included_names,
        excluded_items=excluded_names,
        rationale=(
            f"kept {len(included_names)} components "
            f"(critical always kept; others need confidence>={config.confidence_threshold}); "
            f"excluded {len(excluded_names)}"
        ),
    )
    return included, result
