"""JSON serialization for KnowledgeGraph."""

import json
from typing import Any

from ..models import KnowledgeGraph


class JSONSerializer:
    def serialize(self, graph: KnowledgeGraph) -> str:
        payload: dict[str, Any] = {
            "graph_id": graph.graph_id,
            "document_id": graph.document_id,
            "created_at": graph.created_at.isoformat(),
            "version": graph.version,
            "pipeline_version": graph.pipeline_version,
            "skipped": graph.skipped,
            "reasoning": graph.reasoning,
            "statistics": {
                "total_nodes": graph.statistics.total_nodes,
                "total_edges": graph.statistics.total_edges,
                "node_type_counts": {k.value: v for k, v in graph.statistics.node_type_counts.items()},
                "edge_type_counts": {k.value: v for k, v in graph.statistics.edge_type_counts.items()},
                "average_degree": graph.statistics.average_degree,
                "max_degree": graph.statistics.max_degree,
                "connected_components": graph.statistics.connected_components,
                "diameter": graph.statistics.diameter,
                "clustering_coefficient": graph.statistics.clustering_coefficient,
            },
            "confidence": {
                "overall_confidence": graph.confidence.overall_confidence,
                "formula": graph.confidence.formula,
                "distribution": {
                    "high": graph.confidence.confidence_distribution.high,
                    "medium": graph.confidence.confidence_distribution.medium,
                    "low": graph.confidence.confidence_distribution.low,
                    "mean": graph.confidence.confidence_distribution.mean,
                    "median": graph.confidence.confidence_distribution.median,
                    "std_dev": graph.confidence.confidence_distribution.std_dev,
                },
            },
            "nodes": [
                {
                    "id": n.node_id,
                    "type": n.node_type.value,
                    "label": n.label,
                    "properties": n.properties,
                    "confidence": n.confidence,
                    "source_entity_id": n.source_entity_id,
                    "evidence": [
                        {
                            "page": e.page,
                            "section": e.section.value if e.section is not None else None,
                            "snippet": e.text_snippet,
                            "confidence": e.confidence,
                        }
                        for e in n.evidence_references
                    ],
                }
                for n in graph.nodes
            ],
            "edges": [
                {
                    "id": e.edge_id,
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "type": e.edge_type.value,
                    "label": e.label,
                    "properties": e.properties,
                    "direction": e.direction.value,
                    "confidence": e.confidence,
                }
                for e in graph.edges
            ],
            "warnings": graph.warnings,
        }
        return json.dumps(payload, indent=2, default=str)
