"""Evidence-strength weighting using the configured formula components."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.document_understanding.models import EvidenceReference

from ..config import KnowledgeGraphConfig
from ..interfaces import BaseWeightCalculator
from ..models import GraphEdge, GraphNode


class EvidenceWeightCalculator(BaseWeightCalculator):
    """Implements: 0.5*confidence + 0.3*evidence_count + 0.2*source_quality
    where evidence_count is scaled to [0,1] and source_quality defaults to
    mean evidence-reference confidence (or 0.5 if none)."""

    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()

    def calculate_confidence(
        self,
        node: Optional[GraphNode],
        edge: Optional[GraphEdge],
        evidence: list[EvidenceReference],
        node_lookup: Optional[dict[str, GraphNode]] = None,
    ) -> float:
        base = node.confidence if node is not None else (edge.confidence if edge is not None else 0.5)
        evidence_count = min(1.0, len(evidence) / 5.0)
        if evidence:
            source_quality = sum(e.confidence for e in evidence) / len(evidence)
        else:
            source_quality = 0.5
        return min(1.0, 0.5 * base + 0.3 * evidence_count + 0.2 * source_quality)

    def supports(self, context: AnalysisContext) -> bool:
        return True
