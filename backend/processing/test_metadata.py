"""Tests for backend/processing/metadata.py.

Operates directly on ParsedPDF (constructed by hand), not real PDF
files — MetadataExtractor's input contract is ParsedPDF, and parser.py
already has its own dedicated tests proving PDFParser produces that
shape correctly from a real file.

Run: pytest backend/processing/test_metadata.py -v
"""

from backend.processing.metadata import MetadataExtractor
from backend.processing.models import ParsedPDF
from backend.processing.sections import SectionExtractor

extractor = MetadataExtractor()


def _parsed(first_page_text: str, raw_text: str | None = None, pdf_metadata: dict | None = None) -> ParsedPDF:
    return ParsedPDF(
        raw_text=raw_text if raw_text is not None else first_page_text,
        first_page_text=first_page_text,
        page_count=1,
        text_page_count=1,
        pdf_metadata=pdf_metadata or {},
        is_likely_scanned=False,
    )


def test_title_prefers_native_pdf_metadata():
    parsed = _parsed("Some heuristic-only line.", pdf_metadata={"title": "The Real Title From Metadata"})
    result = extractor.extract(parsed)
    assert result.title == "The Real Title From Metadata"
    assert result.confidence["title"] == 0.9


def test_title_falls_back_to_first_substantial_line():
    parsed = _parsed("A Sufficiently Long Paper Title Here\nJane Doe")
    result = extractor.extract(parsed)
    assert result.title == "A Sufficiently Long Paper Title Here"
    assert result.confidence["title"] == 0.5


def test_title_rejects_urls_and_page_numbers_as_first_line():
    parsed = _parsed("https://example.com/paper\nPage 1\nA Real Title Line Follows Here")
    result = extractor.extract(parsed)
    assert result.title == "A Real Title Line Follows Here"


def test_title_absent_when_nothing_plausible_found():
    parsed = _parsed("hi\nok\nno")
    result = extractor.extract(parsed)
    assert result.title == ""
    assert result.confidence["title"] == 0.0


def test_authors_from_native_metadata_split_on_semicolon():
    parsed = _parsed("body", pdf_metadata={"author": "Jane Doe; John Smith"})
    result = extractor.extract(parsed)
    assert result.authors == ["Jane Doe", "John Smith"]
    assert result.confidence["authors"] == 0.8


def test_authors_heuristic_from_byline_pattern():
    parsed = _parsed("A Paper Title\nJane Doe, John Smith\nAbstract")
    result = extractor.extract(parsed)
    assert result.authors == ["Jane Doe", "John Smith"]
    assert result.confidence["authors"] == 0.4


def test_venue_detected_from_marker_phrase():
    parsed = _parsed("A Title\nJane Doe\nIn Proceedings of the 2024 Conference on Widgets")
    result = extractor.extract(parsed)
    assert "Proceedings of" in result.venue


def test_venue_empty_when_no_marker_found():
    parsed = _parsed("A Title\nJane Doe\nSome unrelated line.")
    result = extractor.extract(parsed)
    assert result.venue == ""
    assert result.confidence["venue"] == 0.0


def test_year_from_pdf_creation_date():
    parsed = _parsed("body", pdf_metadata={"creationDate": "D:20230615120000+00'00'"})
    result = extractor.extract(parsed)
    assert result.year == 2023
    assert result.confidence["year"] == 0.6


def test_year_heuristic_from_page_text():
    parsed = _parsed("A Title\nPublished 2019 in some venue")
    result = extractor.extract(parsed)
    assert result.year == 2019
    assert result.confidence["year"] == 0.4


def test_doi_extracted_via_regex():
    parsed = _parsed("A Title\nhttps://doi.org/10.1234/abcd.5678")
    result = extractor.extract(parsed)
    assert result.doi == "10.1234/abcd.5678"
    assert result.confidence["doi"] == 0.95


def test_doi_absent_returns_none():
    parsed = _parsed("A Title\nNo DOI here.")
    result = extractor.extract(parsed)
    assert result.doi is None


def test_abstract_from_own_fallback_heuristic():
    parsed = _parsed("A Title\nJane Doe\nAbstract\nThis is the abstract body text.")
    result = extractor.extract(parsed)
    assert result.abstract == "This is the abstract body text."
    assert result.confidence["abstract"] == 0.5


def test_abstract_prefers_section_extractor_result_when_given():
    text = "Abstract\nSection-extracted abstract text.\n\nIntroduction\nIntro."
    sections = SectionExtractor().extract(text)
    parsed = _parsed(first_page_text="Abstract\nSomething different heuristically.", raw_text=text)

    result = extractor.extract(parsed, sections=sections)

    assert result.abstract == "Section-extracted abstract text."
    assert result.confidence["abstract"] == 0.9


def test_keywords_extracted_from_labelled_line():
    parsed = _parsed("A Title\nKeywords: machine learning, neural networks, benchmarks")
    result = extractor.extract(parsed)
    assert result.keywords == ["machine learning", "neural networks", "benchmarks"]
    assert result.confidence["keywords"] == 0.6


def test_keywords_empty_when_no_label_found():
    parsed = _parsed("A Title\nNo keyword label here.")
    result = extractor.extract(parsed)
    assert result.keywords == []


def test_every_field_has_a_confidence_and_reasoning_entry():
    parsed = _parsed("A Title\nJane Doe")
    result = extractor.extract(parsed)
    for field in ("title", "authors", "venue", "year", "doi", "abstract", "keywords"):
        assert field in result.confidence
        assert field in result.reasoning
        assert result.reasoning[field]  # non-empty explanation either way
