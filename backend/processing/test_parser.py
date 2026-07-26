"""Tests for backend/processing/parser.py, against real PDFs generated
on the fly with PyMuPDF (already a project dependency — see requirements.txt)
rather than binary fixture files checked into the repo.

Run: pytest backend/processing/test_parser.py -v
"""

import os

import fitz
import pytest

from backend.processing.parser import PDFParser


def _make_pdf(tmp_path, pages: list[str], metadata: dict | None = None) -> str:
    """Writes a real PDF with one page per string in `pages` (each
    inserted as plain text) and returns its path. `tmp_path` is pytest's
    own per-test temp directory fixture — no hardcoded path anywhere."""
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


@pytest.fixture
def parser():
    return PDFParser()


def test_parses_a_real_two_page_pdf(tmp_path, parser):
    path = _make_pdf(
        tmp_path,
        pages=["A Real Paper Title\nJane Doe", "Introduction\nBackground text here."],
    )
    result = parser.parse(path, "application/pdf", "sample.pdf")

    assert result.page_count == 2
    assert result.text_page_count == 2
    assert result.is_likely_scanned is False
    assert "A Real Paper Title" in result.first_page_text
    assert "Introduction" in result.raw_text
    # Page sentinels must not leak into the returned text.
    assert "\x00" not in result.raw_text
    assert "\x00" not in result.first_page_text


def test_first_page_text_excludes_later_pages(tmp_path, parser):
    path = _make_pdf(tmp_path, pages=["Page one content only.", "Page two content only."])
    result = parser.parse(path, "application/pdf", "sample.pdf")

    assert "Page one content" in result.first_page_text
    assert "Page two content" not in result.first_page_text
    assert "Page two content" in result.raw_text


def test_reads_native_pdf_metadata(tmp_path, parser):
    path = _make_pdf(
        tmp_path,
        pages=["Some content."],
        metadata={"title": "Metadata Title", "author": "Metadata Author"},
    )
    result = parser.parse(path, "application/pdf", "sample.pdf")

    assert result.pdf_metadata["title"] == "Metadata Title"
    assert result.pdf_metadata["author"] == "Metadata Author"


def test_blank_page_with_no_text_is_flagged_as_likely_scanned(tmp_path):
    doc = fitz.open()
    doc.new_page()  # no insert_text call at all — genuinely no text layer
    path = os.path.join(tmp_path, "blank.pdf")
    doc.save(path)
    doc.close()

    result = PDFParser().parse(path, "application/pdf", "blank.pdf")

    assert result.page_count == 1
    assert result.text_page_count == 0
    assert result.is_likely_scanned is True
    assert result.raw_text == ""


def test_nonexistent_file_fails_soft_with_empty_metadata(parser):
    result = parser.parse("/no/such/file.pdf", "application/pdf", "file.pdf")
    assert result.page_count == 0
    assert result.pdf_metadata == {}
