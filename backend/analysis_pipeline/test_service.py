"""Unit tests for Phase 2 AnalysisPipelineService (no DB)."""

from pathlib import Path

import fitz
import pytest

from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisOptions
from backend.analysis_pipeline.serialize import to_jsonable
from backend.analysis_pipeline.service import AnalysisPipelineService, extract_bibliographic_fields
from backend.analysis_pipeline.summary import build_phase1_prompt_context, classification_domain_hint


def _make_pdf(tmp_path: Path, text: str) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in text.splitlines():
        page.insert_text((72, y), line)
        y += 14
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


def test_to_jsonable_enums_and_nested():
    from backend.knowledge_graph.enums import NodeType

    assert to_jsonable(NodeType.DISEASE) == "disease"
    assert to_jsonable({"a": [1, NodeType.STUDY]})["a"][1] == "study"


def test_pipeline_runs_all_phases(tmp_path):
    path = _make_pdf(
        tmp_path,
        "Metformin for Type 2 Diabetes\n\n"
        "Abstract\nRandomized controlled trial of metformin in adults.\n\n"
        "Methods\nPatients received metformin 1000mg daily.\n\n"
        "Results\nHbA1c decreased significantly.\n",
    )
    result = AnalysisPipelineService().analyze_file_path(
        path,
        file_id=42,
        options=AnalysisOptions(persist_graph_formats=False),
    )
    assert result.status in (AnalysisJobStatus.DONE, AnalysisJobStatus.PARTIAL)
    assert "document_understanding" in result.phase_results
    assert "classification" in result.phase_results
    assert "analysis_context" in result.phase_results
    assert "medical_understanding" in result.phase_results
    assert "evidence_grading" in result.phase_results
    assert "prompt_assembly" in result.phase_results
    assert "knowledge_graph" in result.phase_results
    assert result.total_processing_time_ms > 0
    assert result.content_hash


def test_prompt_context_and_domain_hint():
    phases = {
        "classification": {"domain": {"label": "medicine", "confidence": 0.9}},
        "medical_understanding": {
            "skipped": False,
            "pico_elements": {
                "population": {"description": "Adults with T2D"},
                "interventions": [{"name": "Metformin"}],
                "outcomes": [{"name": "HbA1c"}],
            },
            "clinical_entities": [{"value": "Metformin", "entity_type": "drug"}],
        },
        "knowledge_graph": {"statistics": {"total_nodes": 3, "total_edges": 2, "average_degree": 1.3}},
    }
    ctx = build_phase1_prompt_context(phases)
    assert "Metformin" in ctx
    assert classification_domain_hint(phases) == "medical"
    fields = extract_bibliographic_fields(
        {"document_understanding": {"metadata": {"title": "A Study", "authors": ["A", "B"], "doi": "10.1/x"}}}
    )
    assert fields["title"] == "A Study"
    assert "A" in fields["authors"]
