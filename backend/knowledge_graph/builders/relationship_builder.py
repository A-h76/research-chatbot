"""Builds GraphEdges from entity co-occurrence + PICO structure.

ClinicalRelation is produced inside medical_understanding.post_processor
but is NOT attached to MedicalUnderstanding — this builder re-applies the
same (subject_type, object_type) → relation_type mapping against
clinical_entities, then adds PICO structural edges.
"""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.enums import ClinicalEntityType, ClinicalRelationType
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import KnowledgeGraphConfig
from ..enums import EdgeType, NodeType
from ..interfaces import BaseEdgeBuilder
from ..models import GraphEdge, GraphNode
from .edge_builder import EdgeBuilderHelper

_RELATION_TYPE_BY_ENTITY_PAIR: dict[tuple[ClinicalEntityType, ClinicalEntityType], ClinicalRelationType] = {
    (ClinicalEntityType.DRUG, ClinicalEntityType.CONDITION): ClinicalRelationType.TREATS,
    (ClinicalEntityType.PROCEDURE, ClinicalEntityType.CONDITION): ClinicalRelationType.TREATS,
    (ClinicalEntityType.CONDITION, ClinicalEntityType.SYMPTOM): ClinicalRelationType.CAUSES,
    (ClinicalEntityType.DRUG, ClinicalEntityType.ADVERSE_EVENT): ClinicalRelationType.CAUSES,
    (ClinicalEntityType.LAB_TEST, ClinicalEntityType.CONDITION): ClinicalRelationType.MEASURED_BY,
}

_CLINICAL_TO_EDGE = {
    ClinicalRelationType.TREATS: EdgeType.TREATS,
    ClinicalRelationType.CAUSES: EdgeType.CAUSES,
    ClinicalRelationType.ASSOCIATED_WITH: EdgeType.ASSOCIATED_WITH,
    ClinicalRelationType.MEASURED_BY: EdgeType.MEASURES,
    ClinicalRelationType.PART_OF: EdgeType.PART_OF,
    ClinicalRelationType.CONTRAINDICATED_WITH: EdgeType.RELATED_TO,
    ClinicalRelationType.OTHER: EdgeType.RELATED_TO,
}


class RelationshipBuilder(BaseEdgeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = EdgeBuilderHelper(sanitize=self._config.sanitize_labels)

    def build_edges(
        self,
        nodes: list[GraphNode],
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        by_source = {n.source_entity_id: n for n in nodes if n.source_entity_id}

        if not medical.skipped:
            entities = [e for e in medical.clinical_entities if e.confidence >= self._config.confidence_threshold]
            for i, subject in enumerate(entities):
                for obj in entities[i + 1 :]:
                    relation = _RELATION_TYPE_BY_ENTITY_PAIR.get((subject.entity_type, obj.entity_type))
                    swapped = False
                    if relation is None:
                        relation = _RELATION_TYPE_BY_ENTITY_PAIR.get((obj.entity_type, subject.entity_type))
                        swapped = relation is not None
                    if relation is None:
                        continue
                    src_key = obj.value if swapped else subject.value
                    tgt_key = subject.value if swapped else obj.value
                    src_node = by_source.get(src_key)
                    tgt_node = by_source.get(tgt_key)
                    if src_node is None or tgt_node is None:
                        continue
                    conf = min(subject.confidence, obj.confidence)
                    evidence = []
                    if subject.evidence is not None:
                        evidence.append(subject.evidence)
                    if obj.evidence is not None:
                        evidence.append(obj.evidence)
                    edges.append(
                        self._helper.make_edge(
                            src_node.node_id,
                            tgt_node.node_id,
                            _CLINICAL_TO_EDGE.get(relation, EdgeType.RELATED_TO),
                            conf,
                            label=relation.value,
                            evidence=evidence,
                        )
                    )

        edges.extend(self._pico_edges(nodes))
        return edges

    def _pico_edges(self, nodes: list[GraphNode]) -> list[GraphEdge]:
        pops = [n for n in nodes if n.node_type == NodeType.POPULATION]
        interventions = [n for n in nodes if n.node_type == NodeType.INTERVENTION]
        comparators = [n for n in nodes if n.node_type == NodeType.COMPARATOR]
        outcomes = [n for n in nodes if n.node_type == NodeType.OUTCOME]
        edges: list[GraphEdge] = []

        for pop in pops:
            for intervention in interventions:
                edges.append(
                    self._helper.make_edge(
                        intervention.node_id,
                        pop.node_id,
                        EdgeType.INTERVENTION_TARGETS,
                        min(intervention.confidence, pop.confidence),
                    )
                )
            for outcome in outcomes:
                edges.append(
                    self._helper.make_edge(
                        pop.node_id,
                        outcome.node_id,
                        EdgeType.POPULATION_HAS,
                        min(pop.confidence, outcome.confidence),
                    )
                )

        for intervention in interventions:
            for outcome in outcomes:
                edges.append(
                    self._helper.make_edge(
                        intervention.node_id,
                        outcome.node_id,
                        EdgeType.OUTCOME_MEASURES,
                        min(intervention.confidence, outcome.confidence),
                    )
                )
            for comparator in comparators:
                edges.append(
                    self._helper.make_edge(
                        intervention.node_id,
                        comparator.node_id,
                        EdgeType.COMPARED_TO,
                        min(intervention.confidence, comparator.confidence),
                    )
                )
        return edges

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 100
