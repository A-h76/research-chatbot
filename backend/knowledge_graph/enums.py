"""Closed label sets for the Knowledge Graph Engine (Phase 1.7)."""

from enum import Enum


class NodeType(str, Enum):
    DISEASE = "disease"
    CONDITION = "condition"
    SYMPTOM = "symptom"
    MEDICATION = "medication"
    TREATMENT = "treatment"
    PROCEDURE = "procedure"
    BIOMARKER = "biomarker"
    LAB_TEST = "lab_test"
    POPULATION = "population"
    INTERVENTION = "intervention"
    COMPARATOR = "comparator"
    OUTCOME = "outcome"
    STUDY = "study"
    AUTHOR = "author"
    ORGANIZATION = "organization"
    JOURNAL = "journal"
    EVIDENCE_CLAIM = "evidence_claim"
    STATISTICAL_RESULT = "statistical_result"
    GRADE_QUALITY = "grade_quality"
    TIMEPOINT = "timepoint"
    LOCATION = "location"
    DEMOGRAPHIC = "demographic"
    PROMPT_COMPONENT = "prompt_component"  # provenance from AssembledPrompt
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    TREATS = "treats"
    CAUSES = "causes"
    PREDICTS = "predicts"
    DIAGNOSES = "diagnoses"
    PREVENTS = "prevents"
    INCREASES_RISK = "increases_risk"
    DECREASES_RISK = "decreases_risk"
    ASSOCIATED_WITH = "associated_with"
    COMPARED_TO = "compared_to"
    MEASURES = "measures"
    POPULATION_HAS = "population_has"
    INTERVENTION_TARGETS = "intervention_targets"
    OUTCOME_MEASURES = "outcome_measures"
    CONDUCTED_BY = "conducted_by"
    PUBLISHED_IN = "published_in"
    CITED_BY = "cited_by"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MODIFIES = "modifies"
    DEPENDS_ON = "depends_on"
    IS_A = "is_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    UNKNOWN = "unknown"


class EdgeDirection(str, Enum):
    DIRECTED = "directed"
    UNDIRECTED = "undirected"
    BIDIRECTIONAL = "bidirectional"


class GraphDecisionType(str, Enum):
    NODE_CREATED = "node_created"
    NODE_MERGED = "node_merged"
    EDGE_CREATED = "edge_created"
    EDGE_WEIGHTED = "edge_weighted"
    CONFIDENCE_CALCULATED = "confidence_calculated"
    RELATIONSHIP_INFERRED = "relationship_inferred"
    DUPLICATE_REMOVED = "duplicate_removed"


class MergeStrategy(str, Enum):
    HIGHEST_CONFIDENCE = "highest_confidence"
    WEIGHTED_AVERAGE = "weighted_average"
    KEEP_ALL = "keep_all"
    CONSENSUS = "consensus"


class ErrorType(str, Enum):
    VALIDATION_ERROR = "validation_error"
    BUILDER_ERROR = "builder_error"
    MERGE_ERROR = "merge_error"
    SERIALIZATION_ERROR = "serialization_error"
    RESOURCE_LIMIT_ERROR = "resource_limit_error"
    SECURITY_ERROR = "security_error"
    GRAPH_ERROR = "graph_error"


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RecoveryType(str, Enum):
    SKIP_BUILDER = "skip_builder"
    TRUNCATE_GRAPH = "truncate_graph"
    DROP_INFERRED = "drop_inferred"
    FALLBACK_EMPTY = "fallback_empty"
    RETRY = "retry"
