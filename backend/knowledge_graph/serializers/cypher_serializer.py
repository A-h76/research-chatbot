"""Cypher CREATE statements for Neo4j import (opt-in serialization)."""

from ..models import KnowledgeGraph
from ..security.sanitizers import escape_cypher_string


class CypherSerializer:
    def serialize(self, graph: KnowledgeGraph) -> str:
        lines: list[str] = [f"// Knowledge graph {graph.graph_id} for document {graph.document_id}"]
        for node in graph.nodes:
            label = escape_cypher_string(node.label)
            ntype = "".join(c for c in node.node_type.value.title() if c.isalnum()) or "Node"
            lines.append(
                f"CREATE (:{ntype} {{id: '{node.node_id}', label: '{label}', "
                f"confidence: {node.confidence:.4f}}});"
            )
        for edge in graph.edges:
            rel = "".join(c if c.isalnum() else "_" for c in edge.edge_type.value.upper())
            lines.append(
                f"MATCH (a {{id: '{edge.source_node_id}'}}), (b {{id: '{edge.target_node_id}'}}) "
                f"CREATE (a)-[:{rel} {{confidence: {edge.confidence:.4f}}}]->(b);"
            )
        return "\n".join(lines)
