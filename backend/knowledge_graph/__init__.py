"""Knowledge Graph Construction Engine — Phase 1.7.

Consumes ProcessedDocument, ClassificationResult, AnalysisContext,
MedicalUnderstanding, EvidenceGrades, and AssembledPrompt and produces
a KnowledgeGraph with nodes, edges, confidence, statistics, evidence
trail, and optional JSON/GraphML(/Cypher) serializations.

Design notes vs the originating task:
- ClinicalRelation is not on MedicalUnderstanding — edges rebuilt from
  entity-type co-occurrence (same rules as medical post_processor) + PICO.
- ClinicalEntity has value/entity_type (no entity_id/normalized_value).
- PICO population is singular Optional[Population].
- OutcomeGrade has no effect_size/CI/p_value fields.
- Semantic weights use token Jaccard (no embedding dependency).
- Diameter/clustering computed only for small graphs.
- Always builds at least STUDY provenance nodes when medical/grades skip.

Non-goals: graph DB persistence, query engine, LLM, UI/API/DB changes.
"""

from .config import KnowledgeGraphConfig
from .enums import (
    EdgeDirection,
    EdgeType,
    ErrorSeverity,
    ErrorType,
    GraphDecisionType,
    MergeStrategy,
    NodeType,
    RecoveryType,
)
from .models import (
    ConfidenceCalculation,
    ConfidenceDistribution,
    EvidenceTrail,
    ExtractionError,
    GraphConfidence,
    GraphDecision,
    GraphEdge,
    GraphNode,
    GraphStatistics,
    KnowledgeGraph,
    RecoveryAction,
)
from .pipeline import KnowledgeGraphPipeline

__all__ = [
    "KnowledgeGraphPipeline",
    "KnowledgeGraphConfig",
    "KnowledgeGraph",
    "GraphNode",
    "GraphEdge",
    "GraphStatistics",
    "GraphConfidence",
    "ConfidenceDistribution",
    "EvidenceTrail",
    "GraphDecision",
    "ConfidenceCalculation",
    "ExtractionError",
    "RecoveryAction",
    "NodeType",
    "EdgeType",
    "EdgeDirection",
    "GraphDecisionType",
    "MergeStrategy",
    "ErrorType",
    "ErrorSeverity",
    "RecoveryType",
]
