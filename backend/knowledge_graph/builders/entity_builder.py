"""Builds GraphNodes from MedicalUnderstanding.clinical_entities."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.enums import ClinicalEntityType
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import KnowledgeGraphConfig
from ..enums import NodeType
from ..interfaces import BaseNodeBuilder
from ..models import GraphNode
from .node_builder import NodeBuilderHelper

_ENTITY_TYPE_MAP = {
    ClinicalEntityType.CONDITION: NodeType.CONDITION,
    ClinicalEntityType.DRUG: NodeType.MEDICATION,
    ClinicalEntityType.PROCEDURE: NodeType.PROCEDURE,
    ClinicalEntityType.SYMPTOM: NodeType.SYMPTOM,
    ClinicalEntityType.LAB_TEST: NodeType.LAB_TEST,
    ClinicalEntityType.BIOMARKER: NodeType.BIOMARKER,
    ClinicalEntityType.DEVICE: NodeType.TREATMENT,
    ClinicalEntityType.ADVERSE_EVENT: NodeType.CONDITION,
    ClinicalEntityType.ANATOMICAL_SITE: NodeType.LOCATION,
    ClinicalEntityType.OTHER: NodeType.UNKNOWN,
}


class EntityNodeBuilder(BaseNodeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = NodeBuilderHelper(
            sanitize=self._config.sanitize_labels,
            max_label_length=self._config.max_label_length,
        )

    def build_nodes(self, medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[GraphNode]:
        if medical.skipped:
            return []
        nodes: list[GraphNode] = []
        for entity in medical.clinical_entities:
            if entity.confidence < self._config.confidence_threshold:
                continue
            node_type = _ENTITY_TYPE_MAP.get(entity.entity_type, NodeType.UNKNOWN)
            evidence = [entity.evidence] if entity.evidence is not None else []
            nodes.append(
                self._helper.make_node(
                    node_type=node_type,
                    label=entity.value or entity.raw_text,
                    confidence=entity.confidence,
                    properties={
                        "raw_text": entity.raw_text,
                        "entity_type": entity.entity_type.value,
                        "normalization_status": entity.normalization_status.value,
                        "synonyms": list(entity.synonyms),
                    },
                    evidence=evidence,
                    source_entity_id=entity.value,
                )
            )
        return nodes

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 100
