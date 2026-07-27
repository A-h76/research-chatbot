"""Tests for backend/processing/__init__.py's process_pdf() orchestration
— the full PDFParser -> MetadataExtractor -> SectionExtractor ->
QualityAssessor -> ProcessedDocument chain, against a real PDF generated
on the fly (see test_parser.py's _make_pdf for why: PyMuPDF is already a
project dependency, so this needs no binary fixture file and no new
dependency).

Run: pytest backend/processing/test_pipeline.py -v
"""

import os
from datetime import datetime, timezone

import fitz
import pytest

from backend.processing import DocumentQuality, ProcessedDocument, process_pdf


def _make_pdf(tmp_path, pages: list[str], metadata: dict | None = None) -> str:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        y = 72
        for line in text.splitlines():
            page.insert_text((72, y), line)
            y += 20
    if metadata:
        doc.set_metadata(metadata)
    path = os.path.join(tmp_path, "sample.pdf")
    doc.save(path)
    doc.close()
    return path


_PAGE_1 = "A Realistic Paper Title About Widgets\nJane Doe, John Smith\nAbstract\nThis paper studies widgets."
_PAGE_2 = "Introduction\nBackground on widgets.\n\nMethods\nWe built widgets and measured them."
_PAGE_3 = "Results\nWidgets performed well.\n\nDiscussion\nThis confirms our hypothesis.\n\nReferences\n[1] A citation."


@pytest.fixture
def sample_pdf_path(tmp_path):
    return _make_pdf(
        tmp_path,
        pages=[_PAGE_1, _PAGE_2, _PAGE_3],
        metadata={"title": "A Realistic Paper Title About Widgets", "author": "Jane Doe; John Smith"},
    )


def test_process_pdf_returns_a_fully_populated_processed_document(sample_pdf_path):
    doc = process_pdf(sample_pdf_path, doc_id="123", name="sample.pdf")

    assert isinstance(doc, ProcessedDocument)
    assert doc.id == "123"
    assert doc.title == "A Realistic Paper Title About Widgets"
    assert doc.authors == ["Jane Doe", "John Smith"]
    assert doc.abstract  # picked up via SectionExtractor's "abstract" section
    assert "introduction" in doc.normalized_sections
    assert "methods" in doc.normalized_sections
    assert "results" in doc.normalized_sections
    assert "discussion" in doc.normalized_sections
    assert doc.references == ["[1] A citation."]
    assert doc.page_count == 3
    assert doc.word_count > 0
    assert doc.char_count == len(doc.full_text)
    assert doc.language == "en"
    assert doc.tables == []
    assert doc.figures == []
    assert isinstance(doc.quality, DocumentQuality)
    assert isinstance(doc.created_at, datetime)
    assert doc.created_at.tzinfo == timezone.utc


def test_process_pdf_quality_reflects_the_complete_structure(sample_pdf_path):
    doc = process_pdf(sample_pdf_path, doc_id="1")
    assert doc.quality.missing_sections == []
    assert doc.quality.has_abstract is True
    assert doc.quality.has_methods is True


def test_process_pdf_custom_language_is_passed_through(sample_pdf_path):
    doc = process_pdf(sample_pdf_path, doc_id="1", language="fr")
    assert doc.language == "fr"


def test_process_pdf_on_a_blank_scanned_pdf_flags_low_quality(tmp_path):
    doc_pdf = fitz.open()
    doc_pdf.new_page()
    path = os.path.join(tmp_path, "blank.pdf")
    doc_pdf.save(path)
    doc_pdf.close()

    doc = process_pdf(path, doc_id="1", name="blank.pdf")

    assert doc.title == ""
    assert doc.full_text == ""
    assert doc.quality.errors
    assert doc.quality.confidence < 0.5
