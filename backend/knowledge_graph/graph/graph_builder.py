"""Statistics and confidence calculation for a constructed graph."""

from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Optional

from ..config import KnowledgeGraphConfig
from ..enums import EdgeType, NodeType
from ..models import (
    ConfidenceDistribution,
    GraphConfidence,
    GraphEdge,
    GraphNode,
    GraphStatistics,
)


def build_statistics(nodes: list[GraphNode], edges: list[GraphEdge], config: KnowledgeGraphConfig) -> GraphStatistics:
    node_type_counts: dict[NodeType, int] = defaultdict(int)
    for node in nodes:
        node_type_counts[node.node_type] += 1

    edge_type_counts: dict[EdgeType, int] = defaultdict(int)
    degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, set[str]] = defaultdict(set)

    for edge in edges:
        edge_type_counts[edge.edge_type] += 1
        degree[edge.source_node_id] += 1
        degree[edge.target_node_id] += 1
        adjacency[edge.source_node_id].add(edge.target_node_id)
        adjacency[edge.target_node_id].add(edge.source_node_id)

    n = len(nodes)
    avg_degree = (sum(degree.values()) / n) if n else 0.0
    max_degree = max(degree.values()) if degree else 0
    components = _connected_components([node.node_id for node in nodes], adjacency)
    diameter = None
    clustering = None
    if n and n <= config.max_nodes_for_diameter:
        diameter = _approx_diameter(adjacency, [node.node_id for node in nodes])
        clustering = _clustering_coefficient(adjacency)

    return GraphStatistics(
        total_nodes=n,
        total_edges=len(edges),
        node_type_counts=dict(node_type_counts),
        edge_type_counts=dict(edge_type_counts),
        average_degree=avg_degree,
        max_degree=max_degree,
        connected_components=components,
        diameter=diameter,
        clustering_coefficient=clustering,
    )


def build_confidence(nodes: list[GraphNode], edges: list[GraphEdge]) -> GraphConfidence:
    node_conf = {n.node_id: n.confidence for n in nodes}
    edge_conf = {e.edge_id: e.confidence for e in edges}
    values = list(node_conf.values()) + list(edge_conf.values())
    dist = _distribution(values)
    mean_nodes = mean(node_conf.values()) if node_conf else 0.0
    mean_edges = mean(edge_conf.values()) if edge_conf else 0.0
    coverage = 1.0 if nodes else 0.0
    overall = 0.5 * mean_nodes + 0.3 * mean_edges + 0.2 * coverage
    return GraphConfidence(
        overall_confidence=min(1.0, max(0.0, overall)),
        node_confidence=node_conf,
        edge_confidence=edge_conf,
        confidence_distribution=dist,
    )


def _distribution(values: list[float]) -> ConfidenceDistribution:
    if not values:
        return ConfidenceDistribution()
    n = len(values)
    high = sum(1 for v in values if v > 0.7) / n
    medium = sum(1 for v in values if 0.4 <= v <= 0.7) / n
    low = sum(1 for v in values if v < 0.4) / n
    return ConfidenceDistribution(
        high=high,
        medium=medium,
        low=low,
        mean=mean(values),
        median=median(values),
        std_dev=pstdev(values) if n > 1 else 0.0,
    )


def _connected_components(node_ids: list[str], adjacency: dict[str, set[str]]) -> int:
    seen: set[str] = set()
    count = 0
    for node_id in node_ids:
        if node_id in seen:
            continue
        count += 1
        stack = [node_id]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adjacency.get(current, ()))
    return count


def _bfs_eccentricity(start: str, adjacency: dict[str, set[str]]) -> int:
    dist = {start: 0}
    queue = [start]
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, ()):
            if neighbor not in dist:
                dist[neighbor] = dist[current] + 1
                queue.append(neighbor)
    return max(dist.values()) if dist else 0


def _approx_diameter(adjacency: dict[str, set[str]], node_ids: list[str]) -> Optional[int]:
    if not node_ids:
        return None
    # Exact diameter for small graphs: max eccentricity
    return max(_bfs_eccentricity(node_id, adjacency) for node_id in node_ids)


def _clustering_coefficient(adjacency: dict[str, set[str]]) -> float:
    scores: list[float] = []
    for node, neighbors in adjacency.items():
        k = len(neighbors)
        if k < 2:
            continue
        links = 0
        neighbor_list = list(neighbors)
        for i, a in enumerate(neighbor_list):
            for b in neighbor_list[i + 1 :]:
                if b in adjacency.get(a, ()):
                    links += 1
        scores.append((2 * links) / (k * (k - 1)))
    return mean(scores) if scores else 0.0
