"""Unit tests for builders, merger, serializers, security."""

from backend.knowledge_graph.builders.entity_builder import EntityNodeBuilder
from backend.knowledge_graph.builders.relationship_builder import RelationshipBuilder
from backend.knowledge_graph.config import KnowledgeGraphConfig
from backend.knowledge_graph.enums import EdgeType, MergeStrategy, NodeType
from backend.knowledge_graph.graph.graph_merger import GraphMerger
from backend.knowledge_graph.models import GraphNode
from backend.knowledge_graph.registry import GraphBuilderRegistry
from backend.knowledge_graph.security.sanitizers import LabelSanitizer, escape_cypher_string
from backend.knowledge_graph.serializers.graphml_serializer import GraphMLSerializer
from backend.knowledge_graph.serializers.json_serializer import JSONSerializer
from backend.knowledge_graph.weights.semantic_weights import token_jaccard


def test_entity_builder_maps_drug_and_condition(medical_factory, grades_factory, context_factory):
    nodes = EntityNodeBuilder().build_nodes(medical_factory(), grades_factory())
    types = {n.node_type for n in nodes}
    assert NodeType.MEDICATION in types
    assert NodeType.CONDITION in types


def test_relationship_builder_creates_treats(medical_factory, grades_factory):
    nodes = EntityNodeBuilder().build_nodes(medical_factory(), grades_factory())
    pico_nodes = __import__(
        "backend.knowledge_graph.builders.pico_builder", fromlist=["PICONodeBuilder"]
    ).PICONodeBuilder().build_nodes(medical_factory(), grades_factory())
    all_nodes = nodes + pico_nodes
    edges = RelationshipBuilder().build_edges(all_nodes, medical_factory(), grades_factory())
    assert any(e.edge_type == EdgeType.TREATS for e in edges)
    assert any(e.edge_type == EdgeType.OUTCOME_MEASURES for e in edges)


def test_node_merger_highest_confidence():
    config = KnowledgeGraphConfig(default_merge_strategy=MergeStrategy.HIGHEST_CONFIDENCE)
    registry = GraphBuilderRegistry(config)
    merger = GraphMerger(config, registry)
    nodes = [
        GraphNode(node_type=NodeType.CONDITION, label="Diabetes", confidence=0.5),
        GraphNode(node_type=NodeType.CONDITION, label="diabetes", confidence=0.9),
    ]
    merged = merger.merge_nodes(nodes)
    assert len(merged) == 1
    assert merged[0].confidence == 0.9


def test_json_and_graphml_serializers(medical_factory, grades_factory, prompt_factory, classification_factory, context_factory, pdf_factory):
    from backend.knowledge_graph.conftest import process_pdf
    from backend.knowledge_graph.pipeline import KnowledgeGraphPipeline

    document = process_pdf(pdf_factory(["Title\n"]))
    document.metadata.title = "T"
    graph = KnowledgeGraphPipeline().process(
        document,
        classification_factory(),
        context_factory(),
        medical_factory(),
        grades_factory(),
        prompt_factory(),
    )
    assert '"graph_id"' in JSONSerializer().serialize(graph)
    assert "<graphml" in GraphMLSerializer().serialize(graph)


def test_label_sanitizer_and_cypher_escape():
    assert "<" not in LabelSanitizer().sanitize("<b>Metformin</b>")
    assert "\\'" in escape_cypher_string("O'Brien")


def test_token_jaccard():
    assert token_jaccard("type 2 diabetes", "type 2 diabetes mellitus") > 0.0
    assert token_jaccard("", "x") == 0.0
