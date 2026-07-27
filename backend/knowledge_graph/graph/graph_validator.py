"""Graph structural validation helpers."""

from ..models import GraphEdge, GraphNode


def drop_dangling_edges(nodes: list[GraphNode], edges: list[GraphEdge]) -> tuple[list[GraphEdge], int]:
    node_ids = {n.node_id for n in nodes}
    kept = [e for e in edges if e.source_node_id in node_ids and e.target_node_id in node_ids]
    return kept, len(edges) - len(kept)


def filter_by_confidence(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    threshold: float,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Drop nodes below threshold (except STUDY anchors), then dangling edges."""
    kept_nodes = [
        n
        for n in nodes
        if n.confidence >= threshold or n.node_type.value in ("study", "author", "journal")
    ]
    kept_ids = {n.node_id for n in kept_nodes}
    kept_edges = [
        e
        for e in edges
        if e.source_node_id in kept_ids and e.target_node_id in kept_ids and e.confidence >= threshold * 0.5
    ]
    return kept_nodes, kept_edges
