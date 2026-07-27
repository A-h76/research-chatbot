"""Tests for backend/processing/sections.py.

Run: pytest backend/processing/test_sections.py -v
"""

from backend.processing.sections import SectionExtractor

extractor = SectionExtractor()


def test_detects_bare_line_headings():
    text = "Introduction\nSome intro text.\n\nMethods\nSome methods text."
    result = extractor.extract(text)
    assert result.section_order == ["Introduction", "Methods"]
    assert result.normalized_sections["introduction"] == "Some intro text."
    assert result.normalized_sections["methods"] == "Some methods text."


def test_detects_markdown_headings():
    text = "## Introduction\nIntro body.\n\n## Results\nResults body."
    result = extractor.extract(text)
    assert result.section_order == ["Introduction", "Results"]
    assert "introduction" in result.normalized_sections
    assert "results" in result.normalized_sections


def test_detects_numbered_headings():
    text = "1. Introduction\nIntro body.\n\n2. Methods\nMethods body."
    result = extractor.extract(text)
    assert result.section_order == ["1. Introduction", "2. Methods"]
    assert result.normalized_sections["introduction"] == "Intro body."
    assert result.normalized_sections["methods"] == "Methods body."


def test_detects_underline_style_headings():
    text = "Introduction\n============\nIntro body.\n\nMethods\n-------\nMethods body."
    result = extractor.extract(text)
    assert result.section_order == ["Introduction", "Methods"]
    assert result.normalized_sections["introduction"] == "Intro body."
    # The underline rule line itself must not leak into the section content.
    assert "====" not in result.normalized_sections["introduction"]


def test_bare_line_detector_does_not_misdetect_prose_mentioning_a_keyword():
    # Regression: a full sentence containing "introduction" as a substring
    # must not be treated as its own heading (found during development —
    # see sections.py's own comment on why bare-line matching requires an
    # exact, not partial, normalize_heading() match).
    text = "Introduction\nThis is the introduction with background context.\n\nMethods\nWe did things."
    result = extractor.extract(text)
    assert result.section_order == ["Introduction", "Methods"]
    assert result.normalized_sections["introduction"] == "This is the introduction with background context."


def test_duplicate_raw_headings_get_disambiguated_keys():
    text = "Discussion\nFirst discussion.\n\nDiscussion\nSecond discussion (e.g. in an appendix)."
    result = extractor.extract(text)
    assert "Discussion" in result.raw_sections
    assert "Discussion (2)" in result.raw_sections
    assert result.raw_sections["Discussion"] == "First discussion."
    assert result.raw_sections["Discussion (2)"] == "Second discussion (e.g. in an appendix)."


def test_two_raw_headings_mapping_to_same_normalized_key_are_concatenated():
    # "Discussion" and "Conclusion" both normalize to "discussion" —
    # content from both should be preserved, not overwritten.
    text = "Discussion\nFirst part.\n\nConclusion\nSecond part."
    result = extractor.extract(text)
    assert "First part." in result.normalized_sections["discussion"]
    assert "Second part." in result.normalized_sections["discussion"]


def test_last_section_content_runs_to_end_of_text():
    text = "Introduction\nIntro body.\n\nReferences\n[1] A citation.\n[2] Another citation."
    result = extractor.extract(text)
    assert result.normalized_sections["references"] == "[1] A citation.\n[2] Another citation."


def test_no_headings_found_returns_empty_result_with_zero_confidence():
    result = extractor.extract("Just some plain prose with no headings anywhere in it at all.")
    assert result.section_order == []
    assert result.raw_sections == {}
    assert result.normalized_sections == {}
    assert result.overall_confidence == 0.0


def test_empty_text_returns_empty_result():
    result = extractor.extract("")
    assert result.section_order == []
    assert result.overall_confidence == 0.0


def test_matches_list_carries_per_heading_confidence_and_reasoning():
    text = "Methods\nBody text."
    result = extractor.extract(text)
    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.raw_heading == "Methods"
    assert match.normalized_key == "methods"
    assert match.confidence == 1.0
    assert match.reasoning
