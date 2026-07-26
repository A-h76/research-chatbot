"""Prompt builder / selector registry."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.evidence_grading.models import EvidenceGrades

from .config import PromptAssemblyConfig
from .enums import PromptComponentType, PromptStrategy
from .interfaces import BasePromptBuilder, BaseStrategySelector, BaseTemplateSelector


class PromptBuilderRegistry:
    """Registry for prompt builders and selectors."""

    def __init__(self, config: Optional[PromptAssemblyConfig] = None) -> None:
        self._config = config or PromptAssemblyConfig()
        self._builders: dict[PromptComponentType, list[BasePromptBuilder]] = {}
        self._template_selectors: list[BaseTemplateSelector] = []
        self._strategy_selectors: list[BaseStrategySelector] = []

    def register_builder(self, builder: BasePromptBuilder) -> None:
        self._builders.setdefault(builder.component_type(), []).append(builder)

    def register_template_selector(self, selector: BaseTemplateSelector) -> None:
        self._template_selectors.append(selector)

    def register_strategy_selector(self, selector: BaseStrategySelector) -> None:
        self._strategy_selectors.append(selector)

    def get_enabled_builders(self, context: AnalysisContext) -> list[BasePromptBuilder]:
        enabled: list[BasePromptBuilder] = []
        for builders in self._builders.values():
            for builder in builders:
                if builder.supports(context):
                    enabled.append(builder)
        return sorted(enabled, key=lambda b: (-b.priority(), b.component_type().value))

    def get_template(self, context: AnalysisContext, classification: ClassificationResult) -> str:
        for selector in self._template_selectors:
            if selector.supports(context):
                return selector.select(context, classification)
        return "generic"

    def get_strategy(
        self,
        context: AnalysisContext,
        classification: ClassificationResult,
        grades: EvidenceGrades,
        medical=None,
    ) -> PromptStrategy:
        for selector in self._strategy_selectors:
            if selector.supports(context):
                return selector.select(context, classification, grades, medical)
        return self._config.default_strategy
