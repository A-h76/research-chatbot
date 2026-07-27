from backend.document_understanding.enums import DocumentLanguage, SectionType
from backend.document_understanding.headings import HeadingDetector
from backend.document_understanding.metadata import MetadataExtractor
from backend.document_understanding.models import PageOffset, ParsedDocument
from backend.document_understanding.normalization import HeadingNormalizer
from backend.document_understanding.sections import SectionBuilder
from backend.document_understanding.traceability import TraceabilityBuilder

_TEXT = (
    "A Study of Something Important\nJane Doe, John Smith\n\nJournal of Important Studies\n\n"
    "Abstract\nThis paper studies something important.\n\n"
    "1. Introduction\nSome intro.\n\n"
    "2. Methods\nSome methods.\n\n"
    "DOI: 10.1234/abcd.5678\n"
)


def _build_evidence(pdf_metadata=None):
    parsed = ParsedDocument(
        raw_text=_TEXT,
        first_page_text=_TEXT,
        page_count=1,
        text_page_count=1,
        page_ranges=[PageOffset(page_number=1, start=0, end=len(_TEXT))],
        pdf_metadata=pdf_metadata or {},
    )
    structure = SectionBuilder(HeadingDetector(), HeadingNormalizer()).build(_TEXT)
    metadata = MetadataExtractor().extract(parsed, structure, DocumentLanguage.ENGLISH)
    return parsed, metadata, structure, TraceabilityBuilder().build(parsed, metadata, structure)


def test_located_fact_gets_exact_range_and_full_confidence():
    parsed, metadata, _, evidence = _build_evidence()
    ref = evidence["metadata.doi"]
    assert ref.confidence == 1.0
    start, end = ref.character_range
    assert parsed.raw_text[start:end] == metadata.doi
    assert ref.page == 1


def test_unlocatable_but_real_fact_gets_partial_confidence():
    parsed, metadata, _, evidence = _build_evidence(pdf_metadata={"title": "A Title Never Repeated In Body Text"})
    assert metadata.title == "A Title Never Repeated In Body Text"

    ref = evidence["metadata.title"]
    assert ref.confidence == 0.3
    assert ref.character_range is None
    assert ref.text_snippet == metadata.title


def test_empty_fact_gets_zero_confidence_and_no_span():
    _, metadata, _, evidence = _build_evidence()
    assert metadata.pmid is None

    ref = evidence["metadata.pmid"]
    assert ref.confidence == 0.0
    assert ref.character_range is None
    assert ref.text_snippet == ""


def test_section_evidence_uses_exact_offsets_from_structure():
    parsed, _, structure, evidence = _build_evidence()
    ref = evidence["structure.section.methods"]
    assert ref.section == SectionType.METHODS
    assert ref.confidence == 1.0
    start, end = ref.character_range
    assert parsed.raw_text[start:end] == structure.normalized_headings[SectionType.METHODS]


def test_list_valued_metadata_fields_are_not_covered():
    _, _, _, evidence = _build_evidence()
    assert "metadata.authors" not in evidence
    assert "metadata.keywords" not in evidence
