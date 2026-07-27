"""Builds STUDY / AUTHOR / JOURNAL nodes from ProcessedDocument metadata.

These builders need the document — BaseNodeBuilder only receives
medical/grades. StudyNodeBuilder therefore exposes build_from_document()
used by the pipeline/graph builder, while build_nodes() returns [] when
called through the registry alone (document not available).
"""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import KnowledgeGraphConfig
from ..enums import EdgeType, NodeType
from ..interfaces import BaseEdgeBuilder, BaseNodeBuilder
from ..models import GraphEdge, GraphNode
from .edge_builder import EdgeBuilderHelper
from .node_builder import NodeBuilderHelper


class StudyNodeBuilder(BaseNodeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = NodeBuilderHelper(
            sanitize=self._config.sanitize_labels,
            max_label_length=self._config.max_label_length,
        )
        self._document: Optional[ProcessedDocument] = None
        self._classification: Optional[ClassificationResult] = None

    def bind(self, document: ProcessedDocument, classification: ClassificationResult) -> None:
        self._document = document
        self._classification = classification

    def build_nodes(self, medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[GraphNode]:
        if self._document is None:
            return []
        meta = self._document.metadata
        nodes: list[GraphNode] = []
        title = meta.title or self._document.id
        study_props = {
            "document_id": self._document.id,
            "doi": meta.doi,
            "year": meta.publication_year,
            "study_design": (
                self._classification.study_design.label.value if self._classification is not None else None
            ),
        }
        nodes.append(
            self._helper.make_node(
                NodeType.STUDY,
                title,
                1.0,
                properties=study_props,
                source_entity_id=f"study:{self._document.id}",
            )
        )
        for author in meta.authors[:20]:
            nodes.append(
                self._helper.make_node(
                    NodeType.AUTHOR,
                    author,
                    0.9,
                    source_entity_id=f"author:{author}",
                )
            )
        journal = meta.journal or meta.venue
        if journal:
            nodes.append(
                self._helper.make_node(
                    NodeType.JOURNAL,
                    journal,
                    0.9,
                    source_entity_id=f"journal:{journal}",
                )
            )
        return nodes

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 110


class StudyEdgeBuilder(BaseEdgeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = EdgeBuilderHelper(sanitize=self._config.sanitize_labels)

    def build_edges(
        self,
        nodes: list[GraphNode],
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> list[GraphEdge]:
        studies = [n for n in nodes if n.node_type == NodeType.STUDY]
        authors = [n for n in nodes if n.node_type == NodeType.AUTHOR]
        journals = [n for n in nodes if n.node_type == NodeType.JOURNAL]
        edges: list[GraphEdge] = []
        for study in studies:
            for author in authors:
                edges.append(
                    self._helper.make_edge(author.node_id, study.node_id, EdgeType.CONDUCTED_BY, 0.9)
                )
            for journal in journals:
                edges.append(
                    self._helper.make_edge(study.node_id, journal.node_id, EdgeType.PUBLISHED_IN, 0.9)
                )
        return edges

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 90


class TimepointNodeBuilder(BaseNodeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = NodeBuilderHelper(
            sanitize=self._config.sanitize_labels,
            max_label_length=self._config.max_label_length,
        )

    def build_nodes(self, medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[GraphNode]:
        if medical.skipped or medical.temporal_data is None:
            return []
        temporal = medical.temporal_data
        nodes: list[GraphNode] = []
        for point in temporal.key_timepoints[:50]:
            nodes.append(
                self._helper.make_node(
                    NodeType.TIMEPOINT,
                    point,
                    temporal.confidence,
                    properties={
                        "study_duration": temporal.study_duration,
                        "follow_up_period": temporal.follow_up_period,
                    },
                    evidence=list(temporal.evidence),
                    source_entity_id=f"timepoint:{point}",
                )
            )
        if temporal.study_duration and not temporal.key_timepoints:
            nodes.append(
                self._helper.make_node(
                    NodeType.TIMEPOINT,
                    temporal.study_duration,
                    temporal.confidence,
                    source_entity_id=f"timepoint:duration:{temporal.study_duration}",
                )
            )
        return nodes

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 60
