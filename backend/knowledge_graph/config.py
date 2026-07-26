"""Configuration for the Knowledge Graph Engine."""

from dataclasses import dataclass, field

from .enums import MergeStrategy, NodeType


@dataclass
class KnowledgeGraphConfig:
    max_nodes: int = 1000
    max_edges: int = 5000

    confidence_threshold: float = 0.3
    high_confidence_threshold: float = 0.7

    default_merge_strategy: MergeStrategy = MergeStrategy.HIGHEST_CONFIDENCE
    node_merge_strategies: dict[NodeType, MergeStrategy] = field(default_factory=dict)

    infer_missing_edges: bool = True
    max_inferred_edges: int = 100

    evidence_weight_formula: str = "0.5*confidence + 0.3*evidence_count + 0.2*source_quality"

    default_format: str = "json"
    include_metadata: bool = True
    include_confidence: bool = True
    serialize_json: bool = True
    serialize_graphml: bool = True
    serialize_cypher: bool = False  # opt-in; can be large

    max_graph_size_mb: int = 100
    max_processing_time_ms: int = 30000
    sanitize_labels: bool = True
    max_label_length: int = 500
    max_property_string_length: int = 2000

    enable_parallel: bool = True
    max_parallel_workers: int = 4

    enable_caching: bool = True
    cache_size: int = 50

    verbose_logging: bool = False

    # Soft skip: if medical was skipped AND grades skipped, still build a
    # minimal STUDY/AUTHOR/JOURNAL provenance graph from the document.
    build_minimal_when_skipped: bool = True

    # Diameter BFS is O(n*m); skip for graphs above this node count.
    max_nodes_for_diameter: int = 200
