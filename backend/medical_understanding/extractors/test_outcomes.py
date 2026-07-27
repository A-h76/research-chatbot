from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.enums import OutcomeType
from backend.medical_understanding.extractors.outcomes import OutcomeExtractor


def _extract(pdf_factory, text):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    return OutcomeExtractor().extract(index, None, None, EntityRegistry())


def test_detects_primary_outcome(pdf_factory):
    result = _extract(pdf_factory, "Methods\nThe primary outcome was change in HbA1c.\n")
    outcomes = result.get("outcomes")
    assert any(o.outcome_type == OutcomeType.PRIMARY for o in outcomes)


def test_detects_secondary_outcome(pdf_factory):
    result = _extract(pdf_factory, "Methods\nSecondary outcome was quality of life.\n")
    outcomes = result.get("outcomes")
    assert any(o.outcome_type == OutcomeType.SECONDARY for o in outcomes)


def test_detects_safety_outcome(pdf_factory):
    result = _extract(pdf_factory, "Methods\nThe safety outcome was incidence of adverse events.\n")
    outcomes = result.get("outcomes")
    assert any(o.outcome_type == OutcomeType.SAFETY for o in outcomes)


def test_detects_key_finding_with_significance(pdf_factory):
    result = _extract(pdf_factory, "Results\nThere was a significant reduction in blood pressure.\n")
    findings = result.get("key_findings")
    assert findings and "significant" in findings[0].statement.lower()


def test_no_markers_yields_empty_lists(pdf_factory):
    result = _extract(pdf_factory, "Results\nA generic sentence with no outcome markers.\n")
    assert result.get("outcomes") == []
    assert result.get("key_findings") == []
