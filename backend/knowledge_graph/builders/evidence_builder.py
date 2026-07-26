"""Builds evidence / grade / statistics nodes and SUPPORTS edges."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.evidence_grading.enums import GradingFramework
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import KnowledgeGraphConfig
from ..enums import EdgeType, NodeType
from ..interfaces import BaseEdgeBuilder, BaseNodeBuilder
from ..models import GraphEdge, GraphNode
from .edge_builder import EdgeBuilderHelper
from .node_builder import NodeBuilderHelper


class EvidenceNodeBuilder(BaseNodeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = NodeBuilderHelper(
            sanitize=self._config.sanitize_labels,
            max_label_length=self._config.max_label_length,
        )

    def build_nodes(self, medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[GraphNode]:
        nodes: list[GraphNode] = []

        if not grades.skipped:
            nodes.append(
                self._helper.make_node(
                    NodeType.GRADE_QUALITY,
                    f"grade:{grades.overall_grade.grade_value}",
                    grades.confidence.overall,
                    properties={
                        "grade_value": grades.overall_grade.grade_value,
                        "study_quality": grades.study_quality.value,
                        "risk_of_bias": grades.risk_of_bias.overall_risk.value,
                    },
                    evidence=list(grades.overall_grade.evidence),
                    source_entity_id=f"grade:{grades.overall_grade.grade_value}",
                )
            )
            for name, outcome_grade in grades.outcome_grades.items():
                nodes.append(
                    self._helper.make_node(
                        NodeType.EVIDENCE_CLAIM,
                        f"Evidence: {name}",
                        outcome_grade.confidence,
                        properties={
                            "outcome_name": name,
                            "grade_value": outcome_grade.grade.grade_value,
                        },
                        evidence=list(outcome_grade.evidence),
                        source_entity_id=f"evidence_claim:{name}",
                    )
                )
            grade_fw = grades.framework_results.get(GradingFramework.GRADE)
            if grade_fw is not None and grade_fw.grade_result is not None:
                gr = grade_fw.grade_result
                nodes.append(
                    self._helper.make_node(
                        NodeType.GRADE_QUALITY,
                        f"GRADE:{gr.final_quality.value}",
                        gr.confidence,
                        properties={
                            "initial_quality": gr.initial_quality.value,
                            "final_quality": gr.final_quality.value,
                            "recommendation_strength": (
                                gr.recommendation_strength.value if gr.recommendation_strength else None
                            ),
                        },
                        evidence=list(gr.evidence),
                        source_entity_id=f"grade_framework:{gr.final_quality.value}",
                    )
                )

        if not medical.skipped:
            for measure in medical.statistical_measures:
                if measure.confidence < self._config.confidence_threshold:
                    continue
                evidence = [measure.evidence] if measure.evidence is not None else []
                nodes.append(
                    self._helper.make_node(
                        NodeType.STATISTICAL_RESULT,
                        f"{measure.measure_type.value}: {measure.value}",
                        measure.confidence,
                        properties={
                            "measure_type": measure.measure_type.value,
                            "value": measure.value,
                            "associated_outcome": measure.associated_outcome,
                        },
                        evidence=evidence,
                        source_entity_id=f"stat:{measure.measure_type.value}:{measure.value}",
                    )
                )

        return nodes

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 80


class EvidenceEdgeBuilder(BaseEdgeBuilder):
    """Connect evidence claims / stats to matching outcome nodes."""

    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = EdgeBuilderHelper(sanitize=self._config.sanitize_labels)

    def build_edges(
        self,
        nodes: list[GraphNode],
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> list[GraphEdge]:
        outcomes = {n.label.lower(): n for n in nodes if n.node_type == NodeType.OUTCOME}
        edges: list[GraphEdge] = []
        for node in nodes:
            if node.node_type == NodeType.EVIDENCE_CLAIM:
                outcome_name = str(node.properties.get("outcome_name", "")).lower()
                target = outcomes.get(outcome_name)
                if target is not None:
                    edges.append(
                        self._helper.make_edge(
                            node.node_id,
                            target.node_id,
                            EdgeType.SUPPORTS,
                            node.confidence,
                        )
                    )
            if node.node_type == NodeType.STATISTICAL_RESULT:
                associated = str(node.properties.get("associated_outcome") or "").lower()
                target = outcomes.get(associated) if associated else None
                if target is not None:
                    edges.append(
                        self._helper.make_edge(
                            node.node_id,
                            target.node_id,
                            EdgeType.MEASURES,
                            node.confidence,
                        )
                    )
        return edges

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 70
