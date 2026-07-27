"""Builds GraphNodes from PICOElements (singular population + lists)."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import KnowledgeGraphConfig
from ..enums import NodeType
from ..interfaces import BaseNodeBuilder
from ..models import GraphNode
from .node_builder import NodeBuilderHelper


class PICONodeBuilder(BaseNodeBuilder):
    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        self._config = config or KnowledgeGraphConfig()
        self._helper = NodeBuilderHelper(
            sanitize=self._config.sanitize_labels,
            max_label_length=self._config.max_label_length,
        )

    def build_nodes(self, medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[GraphNode]:
        if medical.skipped or medical.pico_elements is None:
            return []
        pico = medical.pico_elements
        nodes: list[GraphNode] = []

        if pico.population is not None and pico.population.confidence >= self._config.confidence_threshold:
            pop = pico.population
            evidence = [pop.evidence] if pop.evidence is not None else []
            nodes.append(
                self._helper.make_node(
                    NodeType.POPULATION,
                    pop.description or "population",
                    pop.confidence,
                    properties={
                        "sample_size": pop.sample_size,
                        "age_range": pop.age_range,
                        "inclusion_criteria": list(pop.inclusion_criteria),
                        "exclusion_criteria": list(pop.exclusion_criteria),
                    },
                    evidence=evidence,
                    source_entity_id=f"population:{pop.description}",
                )
            )

        for intervention in pico.interventions:
            if intervention.confidence < self._config.confidence_threshold:
                continue
            evidence = [intervention.evidence] if intervention.evidence is not None else []
            nodes.append(
                self._helper.make_node(
                    NodeType.INTERVENTION,
                    intervention.name,
                    intervention.confidence,
                    properties={
                        "intervention_type": intervention.intervention_type.value,
                        "dosage": intervention.dosage,
                        "route": intervention.route,
                        "duration": intervention.duration,
                    },
                    evidence=evidence,
                    source_entity_id=f"intervention:{intervention.name}",
                )
            )

        for comparator in pico.comparators:
            if comparator.confidence < self._config.confidence_threshold:
                continue
            evidence = [comparator.evidence] if comparator.evidence is not None else []
            nodes.append(
                self._helper.make_node(
                    NodeType.COMPARATOR,
                    comparator.name,
                    comparator.confidence,
                    properties={
                        "is_placebo": comparator.is_placebo,
                        "is_active_control": comparator.is_active_control,
                    },
                    evidence=evidence,
                    source_entity_id=f"comparator:{comparator.name}",
                )
            )

        for outcome in pico.outcomes:
            if outcome.confidence < self._config.confidence_threshold:
                continue
            evidence = [outcome.evidence] if outcome.evidence is not None else []
            nodes.append(
                self._helper.make_node(
                    NodeType.OUTCOME,
                    outcome.name,
                    outcome.confidence,
                    properties={
                        "outcome_type": outcome.outcome_type.value,
                        "measurement_method": outcome.measurement_method,
                        "time_point": outcome.time_point,
                    },
                    evidence=evidence,
                    source_entity_id=f"outcome:{outcome.name}",
                )
            )

        return nodes

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 90
