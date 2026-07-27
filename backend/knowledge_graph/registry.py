"""Graph builder registry."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext

from .config import KnowledgeGraphConfig
from .enums import MergeStrategy, NodeType
from .interfaces import BaseEdgeBuilder, BaseNodeBuilder, BaseWeightCalculator


class GraphBuilderRegistry:
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._node_builders: list[BaseNodeBuilder] = []
        self._edge_builders: list[BaseEdgeBuilder] = []
        self._weight_calculators: list[BaseWeightCalculator] = []
        self._merge_strategies: dict[NodeType, MergeStrategy] = dict(self._config.node_merge_strategies)

    def register_node_builder(self, builder: BaseNodeBuilder) -> None:
        self._node_builders.append(builder)

    def register_edge_builder(self, builder: BaseEdgeBuilder) -> None:
        self._edge_builders.append(builder)

    def register_weight_calculator(self, calculator: BaseWeightCalculator) -> None:
        self._weight_calculators.append(calculator)

    def set_merge_strategy(self, node_type: NodeType, strategy: MergeStrategy) -> None:
        self._merge_strategies[node_type] = strategy

    def get_merge_strategy(self, node_type: NodeType) -> MergeStrategy:
        return self._merge_strategies.get(node_type, self._config.default_merge_strategy)

    def enabled_node_builders(self, context: AnalysisContext) -> list[BaseNodeBuilder]:
        return sorted(
            [b for b in self._node_builders if b.supports(context)],
            key=lambda b: -b.priority(),
        )

    def enabled_edge_builders(self, context: AnalysisContext) -> list[BaseEdgeBuilder]:
        return sorted(
            [b for b in self._edge_builders if b.supports(context)],
            key=lambda b: -b.priority(),
        )

    def primary_weight_calculator(self, context: AnalysisContext) -> Optional[BaseWeightCalculator]:
        for calc in self._weight_calculators:
            if calc.supports(context):
                return calc
        return None
