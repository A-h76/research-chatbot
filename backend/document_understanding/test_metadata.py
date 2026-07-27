from backend.document_understanding.enums import DocumentLanguage
from backend.document_understanding.headings import HeadingDetector
from backend.document_understanding.metadata import MetadataExtractor
from backend.document_understanding.models import ParsedDocument
from backend.document_understanding.normalization import HeadingNormalizer
from backend.document_understanding.sections import SectionBuilder

_TEXT = (
    "A Study of Something Important\n"
    "Jane Doe, John Smith\n\n"
    "Journal of Important Studies\n\n"
    "Abstract\n"
    "This paper studies something important.\n\n"
    "1. Introduction\n"
    "Some intro.\n\n"
    "This work is registered at ClinicalTrials.gov under NCT01234567.\n"
    "PMID: 12345678, PMCID: PMC1234567. Preprint arXiv:2107.12345.\n"
    "DOI: 10.1234/abcd.5678\n"
    "This article is distributed under CC BY 4.0.\n"
)


def _extract(structure=None):
    parsed = ParsedDocument(raw_text=_TEXT, first_page_text=_TEXT, page_count=1, text_page_count=1)
    return MetadataExtractor().extract(parsed, structure, DocumentLanguage.ENGLISH)


def _structure():
    return SectionBuilder(HeadingDetector(), HeadingNormalizer()).build(_TEXT)


def test_reuses_legacy_fields_via_composition():
    metadata = _extract(_structure())
    assert metadata.title == "A Study of Something Important"
    assert metadata.authors == ["Jane Doe", "John Smith"]
    assert metadata.doi == "10.1234/abcd.5678"


def test_venue_is_bucketed_as_journal():
    metadata = _extract(_structure())
    assert metadata.venue == "Journal of Important Studies"
    assert metadata.journal == "Journal of Important Studies"
    assert metadata.conference is None


def test_venue_is_bucketed_as_conference():
    text = "In Proceedings of the 2024 Conference on Widgets.\nSome body text follows here."
    parsed = ParsedDocument(raw_text=text, first_page_text=text, page_count=1, text_page_count=1)
    metadata = MetadataExtractor().extract(parsed, None, DocumentLanguage.ENGLISH)
    assert metadata.conference == metadata.venue
    assert metadata.journal is None


def test_extracts_new_identifiers():
    metadata = _extract(_structure())
    assert metadata.pmid == "12345678"
    assert metadata.pmcid == "PMC1234567"
    assert metadata.arxiv_id == "2107.12345"
    assert metadata.clinical_trials_id == "NCT01234567"
    assert metadata.license == "CC BY 4.0"


def test_missing_identifiers_are_none_with_zero_confidence():
    parsed = ParsedDocument(
        raw_text="Just a plain document with no identifiers at all.", first_page_text="Just a plain document."
    )
    metadata = MetadataExtractor().extract(parsed, None, DocumentLanguage.ENGLISH)
    assert metadata.pmid is None
    assert metadata.pmcid is None
    assert metadata.arxiv_id is None
    assert metadata.clinical_trials_id is None
    assert metadata.license is None
    assert metadata.confidence["pmid"] == 0.0


def test_works_without_a_structure_argument():
    metadata = _extract(structure=None)
    assert metadata.doi == "10.1234/abcd.5678"


def test_always_leaves_unextractable_fields_empty():
    metadata = _extract(_structure())
    assert metadata.subtitle is None
    assert metadata.affiliations == []
    assert metadata.corresponding_author is None
    assert metadata.publication_type is None
