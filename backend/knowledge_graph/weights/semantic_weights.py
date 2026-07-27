"""Semantic similarity weighting — token-overlap proxy (no embeddings).

Honest limitation: without an embedding model this cannot compute true
semantic similarity. Jaccard overlap of label tokens is used as a
deterministic, dependency-free proxy for optional edge re-weighting.
"""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.document_understanding.models import EvidenceReference

from ..interfaces import BaseWeightCalculator
from ..models import GraphEdge, GraphNode


def token_jaccard(a: str, b: str) -> float:
    ta = {t.lower() for t in (a or "").split() if t}
    tb = {t.lower() for t in (b or "").split() if t}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


class SemanticWeightCalculator(BaseWeightCalculator):
    def calculate_confidence(
        self,
        node: Optional[GraphNode],
        edge: Optional[GraphEdge],
        evidence: list[EvidenceReference],
        node_lookup: Optional[dict[str, GraphNode]] = None,
    ) -> float:
        if edge is None:
            return node.confidence if node is not None else 0.5
        lookup = node_lookup or {}
        source = lookup.get(edge.source_node_id)
        target = lookup.get(edge.target_node_id)
        if source is None or target is None:
            return edge.confidence
        overlap = token_jaccard(source.label, target.label)
        return min(1.0, 0.7 * edge.confidence + 0.3 * overlap)

    def supports(self, context: AnalysisContext) -> bool:
        return True
