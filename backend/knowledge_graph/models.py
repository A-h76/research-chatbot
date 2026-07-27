"""Dataclasses for the Knowledge Graph Engine.

Upstream API gaps vs the originating task (handled here, not invented
fields on Phase 1.4 models):
- ClinicalEntity has value/entity_type/raw_text — no entity_id,
  normalized_value, relations list on the entity.
- ClinicalRelation exists but is NOT attached to MedicalUnderstanding;
  relationship edges are rebuilt from entity-type co-occurrence (same
  rules as medical_understanding.post_processor) plus PICO structure.
- PICOElements.population is Optional[Population], not a list.
- OutcomeGrade has no effect_size/CI/p_value — only grade + confidence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend.document_understanding.models import EvidenceReference

from .enums import (
    EdgeDirection,
    EdgeType,
    ErrorSeverity,
    ErrorType,
    GraphDecisionType,
    NodeType,
    RecoveryType,
)


def new_id() -> str:
    return str(uuid4())


@dataclass
class RecoveryAction:
    action_type: RecoveryType
    description: str
    success: bool
    fallback_value: Any = None


@dataclass
class ExtractionError:
    component: str
    error_type: ErrorType
    message: str
    severity: ErrorSeverity
    recovery_attempted: bool = False
    recovered: bool = False
    recovery_action: Optional[RecoveryAction] = None


@dataclass
class GraphNode:
    node_id: str = field(default_factory=new_id)
    node_type: NodeType = NodeType.UNKNOWN
    label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    evidence_references: list[EvidenceReference] = field(default_factory=list)
    confidence: float = 0.0
    source_entity_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


@dataclass
class GraphEdge:
    edge_id: str = field(default_factory=new_id)
    source_node_id: str = ""
    target_node_id: str = ""
    edge_type: EdgeType = EdgeType.UNKNOWN
    label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    direction: EdgeDirection = EdgeDirection.DIRECTED
    evidence_references: list[EvidenceReference] = field(default_factory=list)
    confidence: float = 0.0
    source_relationship_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


@dataclass
class GraphStatistics:
    total_nodes: int = 0
    total_edges: int = 0
    node_type_counts: dict[NodeType, int] = field(default_factory=dict)
    edge_type_counts: dict[EdgeType, int] = field(default_factory=dict)
    average_degree: float = 0.0
    max_degree: int = 0
    connected_components: int = 0
    diameter: Optional[int] = None
    clustering_coefficient: Optional[float] = None


@dataclass
class ConfidenceDistribution:
    high: float = 0.0  # > 0.7 fraction
    medium: float = 0.0  # 0.4-0.7
    low: float = 0.0  # < 0.4
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0


@dataclass
class GraphConfidence:
    overall_confidence: float = 0.0
    node_confidence: dict[str, float] = field(default_factory=dict)
    edge_confidence: dict[str, float] = field(default_factory=dict)
    confidence_distribution: ConfidenceDistribution = field(default_factory=ConfidenceDistribution)
    formula: str = (
        "0.5*mean_node_confidence + 0.3*mean_edge_confidence + 0.2*coverage"
    )


@dataclass
class ConfidenceCalculation:
    target_id: str
    inputs: dict[str, float] = field(default_factory=dict)
    result: float = 0.0
    formula: str = ""


@dataclass
class GraphDecision:
    decision_id: str = field(default_factory=new_id)
    decision_type: GraphDecisionType = GraphDecisionType.NODE_CREATED
    description: str = ""
    rule_applied: str = ""
    evidence: list[EvidenceReference] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EvidenceTrail:
    decisions: list[GraphDecision] = field(default_factory=list)
    node_evidence: dict[str, list[EvidenceReference]] = field(default_factory=dict)
    edge_evidence: dict[str, list[EvidenceReference]] = field(default_factory=dict)
    confidence_calculations: dict[str, ConfidenceCalculation] = field(default_factory=dict)

    def add_decision(
        self,
        decision_type: GraphDecisionType,
        description: str,
        rule_applied: str = "",
        confidence: float = 1.0,
        evidence: Optional[list[EvidenceReference]] = None,
    ) -> None:
        self.decisions.append(
            GraphDecision(
                decision_type=decision_type,
                description=description,
                rule_applied=rule_applied,
                evidence=evidence or [],
                confidence=confidence,
            )
        )


@dataclass
class KnowledgeGraph:
    graph_id: str = field(default_factory=new_id)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    document_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    statistics: GraphStatistics = field(default_factory=GraphStatistics)
    confidence: GraphConfidence = field(default_factory=GraphConfidence)
    evidence_trail: EvidenceTrail = field(default_factory=EvidenceTrail)
    warnings: list[str] = field(default_factory=list)
    errors: list[ExtractionError] = field(default_factory=list)
    formats: dict[str, str] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    pipeline_version: str = ""
    skipped: bool = False
    reasoning: Optional[str] = None
