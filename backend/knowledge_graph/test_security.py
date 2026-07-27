"""Security tests for limits and sanitizers."""

from backend.knowledge_graph.config import KnowledgeGraphConfig
from backend.knowledge_graph.models import GraphEdge, GraphNode
from backend.knowledge_graph.security.limits import ResourceGuard
from backend.knowledge_graph.security.sanitizers import LabelSanitizer, sanitize_properties


def test_resource_guard_truncates():
    config = KnowledgeGraphConfig(max_nodes=2, max_edges=1)
    guard = ResourceGuard(config)
    nodes = [GraphNode(label=f"n{i}") for i in range(5)]
    edges = [GraphEdge(source_node_id="a", target_node_id="b") for _ in range(3)]
    assert not guard.check_nodes(5)
    assert len(guard.truncate_nodes(nodes)) == 2
    assert len(guard.truncate_edges(edges)) == 1


def test_sanitize_properties_strips_html_and_controls():
    cleaned = sanitize_properties({"x<script>": "a\x00b<script>c", "ok": 1})
    assert "script" not in cleaned.get("x_script_", "")
    assert cleaned["ok"] == 1
    assert "\x00" not in str(cleaned)


def test_label_sanitizer_truncates():
    sanitizer = LabelSanitizer(max_length=10)
    assert len(sanitizer.sanitize("abcdefghijklmnopqrstuvwxyz")) == 10
