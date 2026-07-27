"""Tests for parser.py, against real PDFs generated on the fly with
PyMuPDF (see conftest.py's make_pdf fixture) — no binary fixtures
checked into the repo.
"""

from pathlib import Path

import fitz
import pytest

from backend.document_understanding.enums import DocumentFormat
from backend.document_understanding.parser import DocumentParser


@pytest.fixture
def parser():
    return DocumentParser()


def test_parses_a_real_two_page_pdf(make_pdf, parser):
    path = make_pdf(["A Real Paper Title\nJane Doe", "Introduction\nBackground text here."])
    result = parser.parse(path, "application/pdf", "sample.pdf")

    assert result.format == DocumentFormat.PDF
    assert result.page_count == 2
    assert result.text_page_count == 2
    assert result.is_likely_scanned is False
    assert "A Real Paper Title" in result.first_page_text
    assert "Introduction" in result.raw_text
    assert "\x00" not in result.raw_text


def test_page_ranges_slice_back_to_each_pages_own_text(make_pdf, parser):
    path = make_pdf(["Page one content only.", "Page two content only."])
    result = parser.parse(path, "application/pdf", "sample.pdf")

    assert len(result.page_ranges) == 2
    page_one, page_two = result.page_ranges
    assert "Page one content" in result.raw_text[page_one.start : page_one.end]
    assert "Page two content" in result.raw_text[page_two.start : page_two.end]
    assert "Page two content" not in result.raw_text[page_one.start : page_one.end]


def test_reads_native_pdf_metadata(make_pdf, parser):
    path = make_pdf(["Some content."], metadata={"title": "Metadata Title", "author": "Metadata Author"})
    result = parser.parse(path, "application/pdf", "sample.pdf")

    assert result.pdf_metadata["title"] == "Metadata Title"
    assert result.pdf_metadata["author"] == "Metadata Author"


def test_blank_page_with_no_text_is_flagged_as_likely_scanned(tmp_path, parser):
    doc = fitz.open()
    doc.new_page()
    path = Path(tmp_path) / "blank.pdf"
    doc.save(str(path))
    doc.close()

    result = parser.parse(path, "application/pdf", "blank.pdf")

    assert result.page_count == 1
    assert result.text_page_count == 0
    assert result.is_likely_scanned is True
    assert result.raw_text == ""


def test_encrypted_pdf_raises_specific_value_error(make_pdf, parser):
    path = make_pdf(["Secret content."], encrypt=True)

    with pytest.raises(ValueError, match="encrypted"):
        parser.parse(path, "application/pdf", "encrypted.pdf")


def test_corrupted_pdf_propagates_its_own_exception(tmp_path, parser):
    path = Path(tmp_path) / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.4 this is not a real pdf body")

    with pytest.raises(Exception):
        parser.parse(path, "application/pdf", "corrupt.pdf")


def test_unsupported_format_returns_empty_tagged_result(tmp_path, parser):
    path = Path(tmp_path) / "notes.txt"
    path.write_text("hello world")

    result = parser.parse(path, "text/plain", "notes.txt")

    assert result.format == DocumentFormat.UNKNOWN
    assert result.raw_text == ""
    assert result.page_count == 0
