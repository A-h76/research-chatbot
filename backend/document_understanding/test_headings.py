from backend.document_understanding.enums import HeadingType
from backend.document_understanding.headings import HeadingDetector


def test_detects_markdown_heading():
    text = "## Introduction\nSome body text."
    candidates = HeadingDetector().detect(text)
    assert len(candidates) == 1
    assert candidates[0].raw_heading == "Introduction"
    assert candidates[0].heading_type == HeadingType.MARKDOWN


def test_detects_numbered_heading():
    text = "1. Introduction\nSome body text."
    candidates = HeadingDetector().detect(text)
    assert candidates[0].raw_heading == "1. Introduction"
    assert candidates[0].heading_type == HeadingType.NUMBERED


def test_detects_underline_heading():
    text = "Introduction\n============\nSome body text."
    candidates = HeadingDetector().detect(text)
    assert candidates[0].raw_heading == "Introduction"
    assert candidates[0].heading_type == HeadingType.UNDERLINE


def test_detects_bare_heading_on_exact_keyword_match():
    text = "Methods\nWe did an experiment."
    candidates = HeadingDetector().detect(text)
    assert candidates[0].raw_heading == "Methods"
    assert candidates[0].heading_type == HeadingType.BARE


def test_does_not_misdetect_prose_mentioning_a_keyword():
    text = "This is the introduction with background context on the topic at hand."
    candidates = HeadingDetector().detect(text)
    assert candidates == []


def test_offsets_are_exact_character_positions():
    text = "Title line\n\nMethods\nBody content here."
    candidates = HeadingDetector().detect(text)
    heading = next(c for c in candidates if c.raw_heading == "Methods")
    assert text[heading.start_offset : heading.end_offset] == "Methods"


def test_no_headings_returns_empty_list():
    assert HeadingDetector().detect("just a plain paragraph of text, nothing heading-shaped.") == []
