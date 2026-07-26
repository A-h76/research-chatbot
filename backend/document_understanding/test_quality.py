from backend.document_understanding.enums import DocumentLanguage, QualityLevel
from backend.document_understanding.headings import HeadingDetector
from backend.document_understanding.metadata import MetadataExtractor
from backend.document_understanding.models import DocumentMetadata, DocumentStructure, ParsedDocument
from backend.document_understanding.normalization import HeadingNormalizer
from backend.document_understanding.quality import QualityAssessor
from backend.document_understanding.sections import SectionBuilder
from backend.document_understanding.statistics import StatisticsCalculator

_TEXT = (
    "A Study of Something Important\nJane Doe, John Smith\n\nJournal of Important Studies\n\n"
    "Abstract\nThis paper studies something important.\n\n"
    "1. Introduction\nSome intro.\n\n"
    "2. Methods\nSome methods.\n\n"
    "Results\nSome results.\n\n"
    "Discussion\nSome discussion.\n\n"
    "DOI: 10.1234/abcd.5678\n"
)


def _assess(text):
    parsed = ParsedDocument(raw_text=text, first_page_text=text, page_count=1, text_page_count=1)
    structure = SectionBuilder(HeadingDetector(), HeadingNormalizer()).build(text)
    metadata = MetadataExtractor().extract(parsed, structure, DocumentLanguage.UNKNOWN)
    statistics = StatisticsCalculator().calculate(parsed, structure)
    return QualityAssessor().assess(parsed, metadata, structure, statistics)


def test_well_formed_document_scores_well_across_dimensions():
    quality = _assess(_TEXT)
    assert quality.ocr_quality > 0.0
    assert quality.metadata_quality > 0.0
    assert quality.section_quality == 1.0  # all 4 core sections present + full detector confidence
    assert quality.layout_quality > 0.0
    assert quality.completeness > 0.0
    assert quality.confidence > 0.5


def test_degenerate_empty_document_is_unusable_with_no_crash():
    parsed = ParsedDocument()
    structure = DocumentStructure()
    metadata = DocumentMetadata()
    statistics = StatisticsCalculator().calculate(parsed, structure)

    quality = QualityAssessor().assess(parsed, metadata, structure, statistics)

    assert quality.confidence == 0.0
    assert quality.level == QualityLevel.UNUSABLE
    assert "No extractable text found in this document." in quality.errors


def test_layout_quality_reflects_strong_vs_bare_heading_ratio():
    all_numbered = "1. Introduction\nText.\n\n2. Methods\nText.\n"
    all_bare = "Introduction\nText.\n\nMethods\nText.\n"

    strong_quality = _assess(all_numbered)
    weak_quality = _assess(all_bare)

    assert strong_quality.layout_quality == 1.0
    assert weak_quality.layout_quality == 0.0


def test_metadata_quality_is_fraction_of_core_fields_populated():
    parsed = ParsedDocument(
        raw_text="No metadata to find here at all.", first_page_text="No metadata to find here at all."
    )
    structure = DocumentStructure()
    metadata = MetadataExtractor().extract(parsed, structure, DocumentLanguage.UNKNOWN)
    statistics = StatisticsCalculator().calculate(parsed, structure)

    quality = QualityAssessor().assess(parsed, metadata, structure, statistics)
    assert 0.0 <= quality.metadata_quality < 1.0
