from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.extractors.comparators import ComparatorExtractor


def _extract(pdf_factory, text):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    return ComparatorExtractor().extract(index, None, None, EntityRegistry())


def test_detects_placebo(pdf_factory):
    result = _extract(pdf_factory, "Abstract\nDesign comparing drug X versus placebo.\n")
    placebo = next(c for c in result.get("comparators") if c.name == "placebo")
    assert placebo.is_placebo is True


def test_detects_standard_care(pdf_factory):
    result = _extract(pdf_factory, "Methods\nControl group received standard care.\n")
    names = [c.name for c in result.get("comparators")]
    assert any("standard" in name.lower() for name in names)


def test_detects_active_control(pdf_factory):
    result = _extract(pdf_factory, "Methods\nThis trial used an active control arm.\n")
    active = [c for c in result.get("comparators") if c.is_active_control]
    assert active


def test_detects_versus_phrase(pdf_factory):
    result = _extract(pdf_factory, "Abstract\nWe compared drug X versus drug Y in this trial.\n")
    names = [c.name for c in result.get("comparators")]
    assert any("versus drug Y" in name for name in names)


def test_no_comparator_language_yields_empty_list(pdf_factory):
    result = _extract(pdf_factory, "Abstract\nA generic sentence about something else.\n")
    assert result.get("comparators") == []
