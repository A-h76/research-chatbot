from backend.document_understanding.enums import SectionType
from backend.document_understanding.normalization import HeadingNormalizer


def test_normalizes_known_heading_with_full_confidence():
    result = HeadingNormalizer().normalize("Methods")
    assert result.section_type == SectionType.METHODS
    assert result.confidence == 1.0
    assert result.reasoning


def test_unknown_heading_normalizes_to_other_with_zero_confidence():
    result = HeadingNormalizer().normalize("A Completely Unrelated Heading")
    assert result.section_type == SectionType.OTHER
    assert result.confidence == 0.0
