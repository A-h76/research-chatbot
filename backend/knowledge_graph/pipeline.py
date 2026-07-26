"""KnowledgeGraphPipeline — Phase 1.7 public entry point.

    Inputs (ProcessedDocument … AssembledPrompt)
        → validate
        → node builders (entity, pico, evidence, study, timepoint)
        → merge nodes
        → edge builders (relationship, evidence, study, inferred)
        → merge edges + drop dangling
        → re-weight + statistics + confidence
        → serialize (json/graphml[/cypher])
        → KnowledgeGraph
"""

import time
from typing import Callable, Optional, TypeVar

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding
from backend.prompt_assembly.models import AssembledPrompt

from .builders.entity_builder import EntityNodeBuilder
from .builders.evidence_builder import EvidenceEdgeBuilder, EvidenceNodeBuilder
from .builders.inferred_edge_builder import InferredEdgeBuilder
from .builders.pico_builder import PICONodeBuilder
from .builders.relationship_builder import RelationshipBuilder
from .builders.study_builder import StudyEdgeBuilder, StudyNodeBuilder, TimepointNodeBuilder
from .config import KnowledgeGraphConfig
from .enums import ErrorSeverity, ErrorType, GraphDecisionType
from .graph.graph_builder import build_confidence, build_statistics
from .graph.graph_merger import GraphMerger
from .graph.graph_validator import drop_dangling_edges, filter_by_confidence
from .models import EvidenceTrail, ExtractionError, GraphEdge, GraphNode, KnowledgeGraph
from .registry import GraphBuilderRegistry
from .security.limits import ResourceGuard
from .serializers.cypher_serializer import CypherSerializer
from .serializers.graphml_serializer import GraphMLSerializer
from .serializers.json_serializer import JSONSerializer
from .validators import require_valid_inputs, validate_inputs, validate_output
from .weights.confidence_weights import ConfidenceWeightCalculator
from .weights.evidence_weights import EvidenceWeightCalculator
from .weights.semantic_weights import SemanticWeightCalculator

PIPELINE_VERSION = "1.0.0"

_Result = TypeVar("_Result")


class KnowledgeGraphPipeline:
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self.config = config or KnowledgeGraphConfig()
        self.registry = GraphBuilderRegistry(self.config)
        self._study_builder = StudyNodeBuilder(self.config)
        self._register_default_builders()
        self._merger = GraphMerger(self.config, self.registry)
        self._guard = ResourceGuard(self.config)

    def _register_default_builders(self) -> None:
        self.registry.register_node_builder(self._study_builder)
        self.registry.register_node_builder(EntityNodeBuilder(self.config))
        self.registry.register_node_builder(PICONodeBuilder(self.config))
        self.registry.register_node_builder(EvidenceNodeBuilder(self.config))
        self.registry.register_node_builder(TimepointNodeBuilder(self.config))

        self.registry.register_edge_builder(RelationshipBuilder(self.config))
        self.registry.register_edge_builder(EvidenceEdgeBuilder(self.config))
        self.registry.register_edge_builder(StudyEdgeBuilder(self.config))
        self.registry.register_edge_builder(InferredEdgeBuilder(self.config))

        self.registry.register_weight_calculator(ConfidenceWeightCalculator())
        self.registry.register_weight_calculator(EvidenceWeightCalculator(self.config))
        self.registry.register_weight_calculator(SemanticWeightCalculator())

    def process(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
        prompt: AssembledPrompt,
    ) -> KnowledgeGraph:
        require_valid_inputs(document, classification, context, medical, grades, prompt)
        start = time.perf_counter()
        warnings = validate_inputs(medical, grades)
        errors: list[ExtractionError] = []
        trail = EvidenceTrail()

        self._study_builder.bind(document, classification)

        all_nodes: list[GraphNode] = []
        for builder in self.registry.enabled_node_builders(context):
            built = self._safe_call(
                builder.__class__.__name__,
                lambda b=builder: b.build_nodes(medical, grades),
                [],
                errors,
            )
            all_nodes.extend(built)
            for node in built:
                trail.add_decision(
                    GraphDecisionType.NODE_CREATED,
                    f"created {node.node_type.value} node {node.label!r}",
                    rule_applied=builder.__class__.__name__,
                    confidence=node.confidence,
                    evidence=node.evidence_references,
                )

        merged_nodes = self._merger.merge_nodes(all_nodes, trail)
        if not self._guard.check_nodes(len(merged_nodes)):
            warnings.append(f"truncating nodes to max_nodes={self.config.max_nodes}")
            merged_nodes = self._guard.truncate_nodes(merged_nodes)

        all_edges: list[GraphEdge] = []
        for builder in self.registry.enabled_edge_builders(context):
            built = self._safe_call(
                builder.__class__.__name__,
                lambda b=builder: b.build_edges(merged_nodes, medical, grades),
                [],
                errors,
            )
            all_edges.extend(built)
            for edge in built:
                decision_type = (
                    GraphDecisionType.RELATIONSHIP_INFERRED
                    if edge.properties.get("inferred")
                    else GraphDecisionType.EDGE_CREATED
                )
                trail.add_decision(
                    decision_type,
                    f"created {edge.edge_type.value} edge",
                    rule_applied=builder.__class__.__name__,
                    confidence=edge.confidence,
                    evidence=edge.evidence_references,
                )

        merged_edges = self._merger.merge_edges(all_edges, trail)
        merged_edges, dangling = drop_dangling_edges(merged_nodes, merged_edges)
        if dangling:
            warnings.append(f"dropped {dangling} dangling edges")

        merged_nodes, merged_edges = filter_by_confidence(
            merged_nodes, merged_edges, self.config.confidence_threshold
        )

        if not self._guard.check_edges(len(merged_edges)):
            warnings.append(f"truncating edges to max_edges={self.config.max_edges}")
            merged_edges = self._guard.truncate_edges(merged_edges)

        # Re-weight with primary calculators
        lookup = {n.node_id: n for n in merged_nodes}
        for calc in (ConfidenceWeightCalculator(), EvidenceWeightCalculator(self.config)):
            for node in merged_nodes:
                node.confidence = calc.calculate_confidence(node, None, node.evidence_references, lookup)
            for edge in merged_edges:
                edge.confidence = calc.calculate_confidence(None, edge, edge.evidence_references, lookup)
                trail.add_decision(
                    GraphDecisionType.EDGE_WEIGHTED,
                    f"weighted edge {edge.edge_id}",
                    rule_applied=calc.__class__.__name__,
                    confidence=edge.confidence,
                )

        # Optional semantic nudge
        semantic = SemanticWeightCalculator()
        for edge in merged_edges:
            edge.confidence = semantic.calculate_confidence(None, edge, edge.evidence_references, lookup)

        # Attach prompt provenance lightly (component count only — not full text dump)
        trail.add_decision(
            GraphDecisionType.CONFIDENCE_CALCULATED,
            f"assembled prompt family={prompt.prompt_family.value} components={len(prompt.components)}",
            rule_applied="AssembledPrompt.provenance",
            confidence=prompt.confidence_score.overall,
        )

        stats = build_statistics(merged_nodes, merged_edges, self.config)
        confidence = build_confidence(merged_nodes, merged_edges)

        for node in merged_nodes:
            trail.node_evidence[node.node_id] = list(node.evidence_references)
        for edge in merged_edges:
            trail.edge_evidence[edge.edge_id] = list(edge.evidence_references)

        graph = KnowledgeGraph(
            nodes=merged_nodes,
            edges=merged_edges,
            document_id=document.id,
            version="1.0.0",
            statistics=stats,
            confidence=confidence,
            evidence_trail=trail,
            warnings=warnings,
            errors=errors,
            processing_time_ms=(time.perf_counter() - start) * 1000,
            pipeline_version=PIPELINE_VERSION,
            skipped=False,
        )

        formats: dict[str, str] = {}
        if self.config.serialize_json:
            formats["json"] = JSONSerializer().serialize(graph)
        if self.config.serialize_graphml:
            formats["graphml"] = GraphMLSerializer().serialize(graph)
        if self.config.serialize_cypher:
            formats["cypher"] = CypherSerializer().serialize(graph)
        graph.formats = formats

        if formats.get("json"):
            size_mb = self._guard.estimate_size_mb(formats["json"])
            if size_mb > self.config.max_graph_size_mb:
                graph.warnings.append(
                    f"serialized JSON size {size_mb:.2f}MB exceeds max_graph_size_mb "
                    f"{self.config.max_graph_size_mb}"
                )

        if graph.processing_time_ms > self.config.max_processing_time_ms:
            graph.warnings.append(
                f"processing exceeded max_processing_time_ms "
                f"({graph.processing_time_ms:.0f}ms > {self.config.max_processing_time_ms}ms)"
            )

        graph.warnings.extend(validate_output(graph, self.config))
        return graph

    @staticmethod
    def _safe_call(
        name: str,
        fn: Callable[[], _Result],
        default: _Result,
        errors: list[ExtractionError],
    ) -> _Result:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            errors.append(
                ExtractionError(
                    component=name,
                    error_type=ErrorType.BUILDER_ERROR,
                    message=str(exc),
                    severity=ErrorSeverity.ERROR,
                )
            )
            return default
