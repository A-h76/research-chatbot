"""Tests for backend/processing/quality.py.

Run: pytest backend/processing/test_quality.py -v
"""

from backend.processing.models import ParsedPDF
from backend.processing.quality import QualityAssessor
from backend.processing.sections import SectionExtractor

assessor = QualityAssessor()
extractor = SectionExtractor()


def _parsed(
    raw_text: str, page_count: int = 1, text_page_count: int | None = None, is_likely_scanned=False
) -> ParsedPDF:
    return ParsedPDF(
        raw_text=raw_text,
        first_page_text=raw_text,
        page_count=page_count,
        text_page_count=text_page_count if text_page_count is not None else page_count,
        pdf_metadata={},
        is_likely_scanned=is_likely_scanned,
    )


_COMPLETE_TEXT = (
    "Abstract\n" + ("word " * 40) + "\n\n"
    "Methods\n" + ("word " * 200) + "\n\n"
    "Results\n" + ("word " * 200) + "\n\n"
    "Discussion\n" + ("word " * 200) + "\n\n"
    "References\n[1] A citation."
)


def test_complete_document_has_no_missing_sections():
    parsed = _parsed(_COMPLETE_TEXT, page_count=3)
    sections = extractor.extract(parsed.raw_text)

    quality = assessor.assess(parsed, sections)

    assert quality.missing_sections == []
    assert quality.has_abstract is True
    assert quality.has_methods is True
    assert quality.has_results is True
    assert quality.has_discussion is True
    assert quality.has_references is True
    assert quality.errors == []


def test_missing_sections_are_listed_and_warned_about():
    parsed = _parsed("Introduction\nSome intro text only, nothing else.", page_count=1)
    sections = extractor.extract(parsed.raw_text)

    quality = assessor.assess(parsed, sections)

    assert set(quality.missing_sections) == {"abstract", "methods", "results", "discussion"}
    assert quality.has_methods is False
    assert any("methods" in w for w in quality.warnings)


def test_likely_scanned_document_gets_zero_ocr_quality_and_an_error():
    parsed = _parsed("", page_count=5, text_page_count=0, is_likely_scanned=True)
    sections = extractor.extract(parsed.raw_text)

    quality = assessor.assess(parsed, sections)

    assert quality.ocr_quality == 0.0
    assert any("scanned" in e.lower() for e in quality.errors)


def test_partial_text_extraction_produces_a_warning_not_an_error():
    parsed = _parsed("Methods\n" + ("word " * 200), page_count=5, text_page_count=2)
    sections = extractor.extract(parsed.raw_text)

    quality = assessor.assess(parsed, sections)

    assert quality.errors == []
    assert any("2 of 5" in w for w in quality.warnings)


def test_sparse_text_relative_to_page_count_lowers_extraction_quality():
    sparse = _parsed("just a few words", page_count=10, text_page_count=10)
    dense = _parsed(_COMPLETE_TEXT, page_count=3, text_page_count=3)

    sparse_sections = extractor.extract(sparse.raw_text)
    dense_sections = extractor.extract(dense.raw_text)

    sparse_quality = assessor.assess(sparse, sparse_sections)
    dense_quality = assessor.assess(dense, dense_sections)

    assert sparse_quality.text_extraction_quality < dense_quality.text_extraction_quality


def test_garbled_text_lowers_ocr_quality():
    clean = _parsed(_COMPLETE_TEXT, page_count=3, text_page_count=3)
    garbled = _parsed("�" * 200 + _COMPLETE_TEXT, page_count=3, text_page_count=3)

    clean_sections = extractor.extract(clean.raw_text)
    garbled_sections = extractor.extract(garbled.raw_text)

    clean_quality = assessor.assess(clean, clean_sections)
    garbled_quality = assessor.assess(garbled, garbled_sections)

    assert garbled_quality.ocr_quality < clean_quality.ocr_quality


def test_confidence_is_between_zero_and_one():
    parsed = _parsed(_COMPLETE_TEXT, page_count=3)
    sections = extractor.extract(parsed.raw_text)
    quality = assessor.assess(parsed, sections)
    assert 0.0 <= quality.confidence <= 1.0


def test_empty_document_produces_an_error_not_just_warnings():
    parsed = _parsed("", page_count=1, text_page_count=1, is_likely_scanned=False)
    sections = extractor.extract(parsed.raw_text)
    quality = assessor.assess(parsed, sections)
    assert quality.errors  # "no extractable text" branch
