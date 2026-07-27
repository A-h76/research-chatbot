from backend.document_understanding.enums import HeadingType, SectionType
from backend.document_understanding.headings import HeadingDetector
from backend.document_understanding.models import DocumentStructure
from backend.document_understanding.normalization import HeadingNormalizer
from backend.document_understanding.sections import SectionBuilder

_TEXT = (
    "Abstract\n"
    "This paper studies something.\n\n"
    "1. Introduction\n"
    "Background context.\n\n"
    "2. Methods\n"
    "Methodology text.\n\n"
    "Discussion\n"
    "First discussion.\n\n"
    "Discussion\n"
    "Second discussion (duplicate heading).\n\n"
    "References\n"
    "[1] A citation.\n"
    "[2] Another citation.\n"
)


def _builder() -> SectionBuilder:
    return SectionBuilder(HeadingDetector(), HeadingNormalizer())


def test_builds_full_structure():
    structure = _builder().build(_TEXT)
    assert structure.heading_order == [
        "Abstract",
        "1. Introduction",
        "2. Methods",
        "Discussion",
        "Discussion",
        "References",
    ]
    assert SectionType.METHODS in structure.normalized_headings
    assert structure.normalized_headings[SectionType.METHODS] == "Methodology text."


def test_duplicate_raw_headings_are_disambiguated_and_content_not_lost():
    structure = _builder().build(_TEXT)
    assert "Discussion" in structure.raw_headings
    assert "Discussion (2)" in structure.raw_headings
    assert structure.raw_headings["Discussion"] == "First discussion."
    assert structure.raw_headings["Discussion (2)"] == "Second discussion (duplicate heading)."


def test_duplicate_normalized_sections_are_merged_not_overwritten():
    structure = _builder().build(_TEXT)
    merged = structure.normalized_headings[SectionType.DISCUSSION]
    assert "First discussion." in merged
    assert "Second discussion (duplicate heading)." in merged


def test_section_offsets_slice_back_to_exact_content():
    structure = _builder().build(_TEXT)
    for key, (start, end) in structure.section_offsets.items():
        assert _TEXT[start:end] == structure.raw_headings[key]


def test_heading_types_and_section_types_tracked_per_key():
    structure = _builder().build(_TEXT)
    assert structure.heading_types["1. Introduction"] == HeadingType.NUMBERED
    assert structure.heading_types["Abstract"] == HeadingType.BARE
    assert structure.section_types["2. Methods"] == SectionType.METHODS


def test_references_parsed_into_list_of_lines():
    structure = _builder().build(_TEXT)
    assert structure.references == ["[1] A citation.", "[2] Another citation."]


def test_no_headings_returns_empty_structure():
    structure = _builder().build("just a plain paragraph, no headings at all here.")
    assert structure == DocumentStructure()
