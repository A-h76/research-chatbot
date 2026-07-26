"""Integration tests for KnowledgeGraphPipeline."""

import json

import pytest

from backend.analysis_context.enums import RoutingDecision
from backend.knowledge_graph.conftest import process_pdf
from backend.knowledge_graph.enums import EdgeType, NodeType
from backend.knowledge_graph.exceptions import ValidationError
from backend.knowledge_graph.pipeline import PIPELINE_VERSION, KnowledgeGraphPipeline
from backend.knowledge_graph.validators import require_valid_inputs


def test_builds_graph_end_to_end(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory, prompt_factory
):
    document = process_pdf(
        pdf_factory(
            [
                "Metformin for Type 2 Diabetes\n\n"
                "Methods\nRandomized trial of metformin.\n\n"
                "Results\nHbA1c improved.\n"
            ]
        )
    )
    # enrich metadata for study nodes
    document.metadata.title = "Metformin for Type 2 Diabetes"
    document.metadata.authors = ["Smith J"]
    document.metadata.journal = "Diabetes Care"

    graph = KnowledgeGraphPipeline().process(
        document,
        classification_factory(),
        context_factory(),
        medical_factory(),
        grades_factory(),
        prompt_factory(),
    )

    assert graph.pipeline_version == PIPELINE_VERSION
    assert graph.skipped is False
    assert graph.statistics.total_nodes >= 3
    assert any(n.node_type == NodeType.STUDY for n in graph.nodes)
    assert any(n.node_type == NodeType.MEDICATION for n in graph.nodes)
    assert any(n.node_type == NodeType.CONDITION for n in graph.nodes)
    assert any(e.edge_type == EdgeType.TREATS for e in graph.edges)
    assert "json" in graph.formats
    payload = json.loads(graph.formats["json"])
    assert payload["statistics"]["total_nodes"] == graph.statistics.total_nodes
    assert 0.0 <= graph.confidence.overall_confidence <= 1.0
    assert graph.evidence_trail.decisions


def test_builds_minimal_graph_when_medical_skipped(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory, prompt_factory
):
    document = process_pdf(pdf_factory(["Generic paper title\n"]))
    document.metadata.title = "Generic paper"
    document.metadata.authors = ["Doe A"]

    graph = KnowledgeGraphPipeline().process(
        document,
        classification_factory(),
        context_factory(primary_routing=RoutingDecision.GENERIC),
        medical_factory(skipped=True),
        grades_factory(skipped=True),
        prompt_factory(),
    )
    assert any(n.node_type == NodeType.STUDY for n in graph.nodes)
    assert graph.warnings


def test_require_valid_inputs(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory, prompt_factory
):
    document = process_pdf(pdf_factory(["x\n"]))
    with pytest.raises(ValidationError):
        require_valid_inputs(
            document,
            classification_factory(),
            context_factory(),
            medical_factory(),
            grades_factory(),
            "bad",  # type: ignore[arg-type]
        )


def test_determinism(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory, prompt_factory
):
    document = process_pdf(pdf_factory(["Metformin diabetes trial\n"]))
    document.metadata.title = "Trial"
    args = (
        document,
        classification_factory(),
        context_factory(),
        medical_factory(),
        grades_factory(),
        prompt_factory(),
    )
    pipeline = KnowledgeGraphPipeline()
    a = pipeline.process(*args)
    b = pipeline.process(*args)
    assert a.statistics.total_nodes == b.statistics.total_nodes
    assert a.statistics.total_edges == b.statistics.total_edges
    assert {n.label for n in a.nodes} == {n.label for n in b.nodes}
