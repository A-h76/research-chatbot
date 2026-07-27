from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import DocumentStructure, PageOffset, ParsedDocument
from backend.document_understanding.utils import (
    page_at_offset,
    paragraph_index_at,
    snippet_at,
    to_legacy_parsed,
    to_legacy_sections,
)


def test_to_legacy_parsed_maps_fields():
    parsed = ParsedDocument(
        raw_text="hello", first_page_text="hello", page_count=1, text_page_count=1, is_likely_scanned=False
    )
    legacy = to_legacy_parsed(parsed)
    assert legacy.raw_text == "hello"
    assert legacy.page_count == 1


def test_to_legacy_sections_drops_other_and_keeps_confidence():
    structure = DocumentStructure(
        heading_order=["Methods", "Random"],
        raw_headings={"Methods": "m", "Random": "r"},
        normalized_headings={SectionType.METHODS: "m", SectionType.OTHER: "r"},
        confidence=0.75,
    )
    legacy = to_legacy_sections(structure)
    assert legacy.normalized_sections == {"methods": "m"}
    assert legacy.overall_confidence == 0.75


def test_page_at_offset_finds_containing_page():
    ranges = [PageOffset(1, 0, 10), PageOffset(2, 10, 20)]
    assert page_at_offset(ranges, 5) == 1
    assert page_at_offset(ranges, 15) == 2


def test_page_at_offset_returns_none_outside_all_ranges():
    ranges = [PageOffset(1, 0, 10)]
    assert page_at_offset(ranges, 50) is None


def test_paragraph_index_at_counts_blank_line_separators():
    text = "para one\n\npara two\n\npara three"
    assert paragraph_index_at(text, 0) == 0
    assert paragraph_index_at(text, text.index("para two")) == 1
    assert paragraph_index_at(text, text.index("para three")) == 2


def test_snippet_at_adds_ellipsis_only_when_truncated():
    text = "x" * 200
    snippet = snippet_at(text, 100, 105, context=10)
    assert snippet.startswith("…")
    assert snippet.endswith("…")

    short_text = "short text here"
    full_snippet = snippet_at(short_text, 0, len(short_text), context=10)
    assert full_snippet == short_text
