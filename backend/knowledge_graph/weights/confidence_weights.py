"""Confidence-based edge/node weighting."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.document_understanding.models import EvidenceReference

from ..interfaces import BaseWeightCalculator
from ..models import GraphEdge, GraphNode


class ConfidenceWeightCalculator(BaseWeightCalculator):
    def calculate_confidence(
        self,
        node: Optional[GraphNode],
        edge: Optional[GraphEdge],
        evidence: list[EvidenceReference],
        node_lookup: Optional[dict[str, GraphNode]] = None,
    ) -> float:
        evidence_boost = min(0.3, len(evidence) * 0.05)
        if node is not None:
            return min(1.0, node.confidence + evidence_boost)
        if edge is not None:
            lookup = node_lookup or {}
            source = lookup.get(edge.source_node_id)
            target = lookup.get(edge.target_node_id)
            source_conf = source.confidence if source else edge.confidence
            target_conf = target.confidence if target else edge.confidence
            return min(1.0, ((source_conf + target_conf) / 2) + evidence_boost)
        return 0.5

    def supports(self, context: AnalysisContext) -> bool:
        return True
