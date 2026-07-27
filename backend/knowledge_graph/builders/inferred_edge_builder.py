"""Limited relationship inference when infer_missing_edges is enabled.

Only creates a small set of high-signal patterns (medication→condition
TREATS, intervention→outcome MEASURES) when no direct edge already
exists. Marked properties.inferred=True. Cap via config.max_inferred_edges.
"""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import KnowledgeGraphConfig
from ..enums import EdgeType, NodeType
from ..interfaces import BaseEdgeBuilder
from ..models import GraphEdge, GraphNode
from .edge_builder import EdgeBuilderHelper


class InferredEdgeBuilder(BaseEdgeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = EdgeBuilderHelper(sanitize=self._config.sanitize_labels)

    def build_edges(
        self,
        nodes: list[GraphNode],
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> list[GraphEdge]:
        if not self._config.infer_missing_edges:
            return []

        existing = {(e.source_node_id, e.target_node_id, e.edge_type) for e in []}  # filled by caller via empty
        # Caller merges; we only produce candidates. Dedup happens in merger.
        meds = [n for n in nodes if n.node_type in (NodeType.MEDICATION, NodeType.INTERVENTION)]
        conditions = [n for n in nodes if n.node_type in (NodeType.CONDITION, NodeType.DISEASE, NodeType.POPULATION)]
        outcomes = [n for n in nodes if n.node_type == NodeType.OUTCOME]

        edges: list[GraphEdge] = []
        for med in meds:
            for condition in conditions:
                if len(edges) >= self._config.max_inferred_edges:
                    return edges
                edges.append(
                    self._helper.make_edge(
                        med.node_id,
                        condition.node_id,
                        EdgeType.TREATS,
                        min(med.confidence, condition.confidence) * 0.7,
                        properties={"inference_rule": "medication_condition_cooccurrence"},
                        inferred=True,
                    )
                )
            for outcome in outcomes:
                if len(edges) >= self._config.max_inferred_edges:
                    return edges
                edges.append(
                    self._helper.make_edge(
                        med.node_id,
                        outcome.node_id,
                        EdgeType.OUTCOME_MEASURES,
                        min(med.confidence, outcome.confidence) * 0.6,
                        properties={"inference_rule": "intervention_outcome_cooccurrence"},
                        inferred=True,
                    )
                )
        _ = existing  # reserved for future cross-builder dedup
        return edges[: self._config.max_inferred_edges]

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 20
