"""Adapters + Phase1Retrieval contract tests."""

from __future__ import annotations

from backend.ai_core.adapters import adapt_citations, adapt_notes, adapt_phase1, adapt_project
from backend.ai_core.context import ResearchContextBuilder
from backend.ai_core.context.phase1_retrieval import MemoryPhase1Source, Phase1Retrieval
from backend.ai_core.schemas.execution import AIExecutionResult, TokenUsage
from backend.ai_core.schemas.ai_response import AIResponse
from backend.ai_core.schemas.research_context import ResearchIntent
from backend.ai_core.orchestration import ResponseValidator
from backend.ai_core.versions import IDENTITY_VERSION


PHASE1_FIXTURE = {
    "document_understanding": {
        "metadata": {"title": "Inflammation and Kupffer cells", "year": "2020"},
        "sections": [
            {"id": "s1", "title": "Results", "text": "CRP was elevated in the treatment arm."},
        ],
    },
    "classification": {
        "document_type": {"label": "RCT", "confidence": 0.9},
        "domain": {"label": "hepatology", "confidence": 0.8},
    },
    "medical_understanding": {
        "skipped": False,
        "clinical_entities": [
            {"id": "e1", "value": "inflammation", "entity_type": "condition", "confidence": 0.91},
            {"value": "CRP", "entity_type": "biomarker", "confidence": 0.88},
        ],
        "pico_elements": {
            "population": {"description": "Adults with chronic liver disease"},
            "outcomes": [{"name": "CRP reduction"}],
        },
    },
    "evidence_grading": {
        "skipped": False,
        "overall_grade": {"grade_value": "B", "confidence": 0.7, "framework": "GRADE"},
        "outcome_grades": {
            "CRP reduction": {
                "confidence": 0.75,
                "grade": {"grade_value": "Moderate"},
            }
        },
    },
    "knowledge_graph": {
        "skipped": False,
        "nodes": [{"id": "n1", "label": "inflammation"}],
        "edges": [],
        "statistics": {"total_nodes": 1, "total_edges": 0},
    },
}


def test_adapt_phase1_extracts_entities_and_evidence():
    bundle = adapt_phase1(PHASE1_FIXTURE)
    assert bundle.document["title"] == "Inflammation and Kupffer cells"
    assert len(bundle.entities) >= 2
    assert any(e["name"] == "inflammation" for e in bundle.entities)
    assert len(bundle.evidence) >= 2
    assert bundle.graph["statistics"]["total_nodes"] == 1
    assert bundle.passages


def test_adapt_notes_citations_project():
    notes = adapt_notes([{"id": 1, "title": "Idea", "content": "x", "file_id": 42}])
    cites = adapt_citations([{"id": 9, "title": "Paper", "authors": "A", "year": "2020"}])
    project = adapt_project({"id": 3, "name": "Thesis", "instructions": "Be careful"})
    assert notes[0]["id"] == 1
    assert cites[0]["year"] == "2020"
    assert project["name"] == "Thesis"


def test_phase1_retrieval_pipeline():
    source = MemoryPhase1Source(
        phase_results_by_file={42: PHASE1_FIXTURE},
        notes=[{"id": 1, "title": "N", "content": "c", "file_id": 42}],
        citations=[{"id": 2, "title": "C", "project_id": 7}],
        projects={7: {"id": 7, "name": "P"}},
    )
    ctx = ResearchContextBuilder(retrieval=Phase1Retrieval(source)).build(
        file_id=42,
        project_id=7,
        intent=ResearchIntent.READING,
        question="Summarise the evidence for inflammation.",
    )
    assert ctx.intent is ResearchIntent.READING
    assert len(ctx.evidence) > 0
    assert len(ctx.entities) > 0
    assert ctx.notes and ctx.citations
    assert ctx.extras["retrieval_meta"]["source"] == "phase1_retrieval"
    assert ctx.extras["retrieval_meta"]["project"]["name"] == "P"


def test_live_retrieval_contract_gate():
    """Integration gate — green via Phase1Retrieval + persistence-shaped fixture."""
    source = MemoryPhase1Source(phase_results_by_file={42: PHASE1_FIXTURE})
    context = ResearchContextBuilder(retrieval=Phase1Retrieval(source)).build(
        file_id=42,
        intent=ResearchIntent.READING,
        question="Summarise the evidence for inflammation.",
    )
    assert len(context.evidence) > 0
    assert len(context.entities) > 0
    assert context.intent == ResearchIntent.READING


def test_ai_execution_result_keeps_response_pure():
    response = AIResponse(answer="ok", confidence="Low", limitations=["thin"])
    validator = ResponseValidator().validate(response)
    result = AIExecutionResult(
        response=response,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        latency_ms=42,
        model="gpt-4o-mini",
        prompt_version="reading_v1",
        identity_version=IDENTITY_VERSION,
        context_schema_version="2.0.0",
        validator=validator,
    )
    assert result.response.answer == "ok"
    assert result.usage.total_tokens == 15
    assert result.identity_version == IDENTITY_VERSION
    assert result.validator and result.validator.ok
