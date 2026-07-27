"""Resource limits for knowledge graph construction."""

from ..config import KnowledgeGraphConfig


class ResourceGuard:
    def __init__(self, config: KnowledgeGraphConfig) -> None:
        self.max_nodes = config.max_nodes
        self.max_edges = config.max_edges
        self.max_inferred_edges = config.max_inferred_edges
        self.max_graph_size_mb = config.max_graph_size_mb

    def check_nodes(self, count: int) -> bool:
        return count <= self.max_nodes

    def check_edges(self, count: int) -> bool:
        return count <= self.max_edges

    def truncate_nodes(self, nodes: list) -> list:
        return nodes[: self.max_nodes]

    def truncate_edges(self, edges: list) -> list:
        return edges[: self.max_edges]

    def estimate_size_mb(self, serialized_json: str) -> float:
        return len(serialized_json.encode("utf-8")) / (1024 * 1024)
