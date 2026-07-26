"""Node and edge merging with configurable strategies."""

from datetime import datetime, timezone
from typing import Optional

from ..config import KnowledgeGraphConfig
from ..enums import GraphDecisionType, MergeStrategy, NodeType
from ..models import EvidenceTrail, GraphEdge, GraphNode
from ..registry import GraphBuilderRegistry


class GraphMerger:
    def __init__(self, config: KnowledgeGraphConfig, registry: GraphBuilderRegistry) -> None:
        self._config = config
        self._registry = registry

    def merge_nodes(self, nodes: list[GraphNode], trail: Optional[EvidenceTrail] = None) -> list[GraphNode]:
        if self._config.default_merge_strategy == MergeStrategy.KEEP_ALL:
            return list(nodes)

        buckets: dict[tuple[NodeType, str], GraphNode] = {}
        for node in nodes:
            key = (node.node_type, node.label.strip().lower())
            if key not in buckets:
                buckets[key] = node
                continue
            existing = buckets[key]
            strategy = self._registry.get_merge_strategy(node.node_type)
            merged = self._merge_pair(existing, node, strategy)
            buckets[key] = merged
            if trail is not None:
                trail.add_decision(
                    GraphDecisionType.NODE_MERGED,
                    f"merged nodes labeled {node.label!r}",
                    rule_applied=strategy.value,
                    confidence=merged.confidence,
                )
        return list(buckets.values())

    def merge_edges(self, edges: list[GraphEdge], trail: Optional[EvidenceTrail] = None) -> list[GraphEdge]:
        buckets: dict[tuple[str, str, str], GraphEdge] = {}
        for edge in edges:
            key = (edge.source_node_id, edge.target_node_id, edge.edge_type.value)
            if key not in buckets:
                buckets[key] = edge
                continue
            existing = buckets[key]
            if edge.confidence > existing.confidence:
                # keep higher confidence, union evidence
                edge.evidence_references = list(existing.evidence_references) + list(edge.evidence_references)
                buckets[key] = edge
                if trail is not None:
                    trail.add_decision(
                        GraphDecisionType.DUPLICATE_REMOVED,
                        f"dropped duplicate edge {existing.edge_id}",
                        rule_applied="highest_confidence",
                        confidence=edge.confidence,
                    )
            else:
                existing.evidence_references = list(existing.evidence_references) + list(edge.evidence_references)
                if trail is not None:
                    trail.add_decision(
                        GraphDecisionType.DUPLICATE_REMOVED,
                        f"dropped duplicate edge {edge.edge_id}",
                        rule_applied="highest_confidence",
                        confidence=existing.confidence,
                    )
        return list(buckets.values())

    @staticmethod
    def _merge_pair(a: GraphNode, b: GraphNode, strategy: MergeStrategy) -> GraphNode:
        if strategy == MergeStrategy.HIGHEST_CONFIDENCE:
            winner, loser = (a, b) if a.confidence >= b.confidence else (b, a)
            winner.evidence_references = list(winner.evidence_references) + list(loser.evidence_references)
            winner.properties = {**loser.properties, **winner.properties}
            winner.updated_at = datetime.now(timezone.utc)
            return winner

        if strategy == MergeStrategy.WEIGHTED_AVERAGE:
            total = a.confidence + b.confidence
            conf = total / 2 if total == 0 else (a.confidence**2 + b.confidence**2) / total
            primary = a if a.confidence >= b.confidence else b
            primary.confidence = min(1.0, conf)
            primary.evidence_references = list(a.evidence_references) + list(b.evidence_references)
            primary.properties = {**a.properties, **b.properties}
            primary.updated_at = datetime.now(timezone.utc)
            return primary

        if strategy == MergeStrategy.CONSENSUS:
            primary = a if a.confidence >= b.confidence else b
            primary.confidence = min(a.confidence, b.confidence)
            primary.evidence_references = list(a.evidence_references) + list(b.evidence_references)
            primary.properties = {**a.properties, **b.properties}
            primary.properties["consensus_merged"] = True
            primary.updated_at = datetime.now(timezone.utc)
            return primary

        return a
