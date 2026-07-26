from backend.analysis_context.section_profile import SectionProfiler
from backend.classification.pass2.enums import DocumentType
from backend.document_understanding.enums import HeadingType, SectionType
from backend.document_understanding.models import DocumentStructure


def test_present_and_missing_sections_relative_to_recommended(document_factory, classification_factory):
    document = document_factory(normalized_headings={SectionType.METHODS: "x" * 200, SectionType.ABSTRACT: "y" * 200})
    classification = classification_factory(document_type=DocumentType.RESEARCH_ARTICLE)

    profile = SectionProfiler().profile(document, classification)

    assert SectionType.METHODS in profile.present_sections
    assert SectionType.RESULTS in profile.missing_sections
    assert SectionType.DISCUSSION in profile.missing_sections
    assert SectionType.METHODS not in profile.missing_sections


def test_thin_section_gets_partial_completeness(document_factory, classification_factory):
    document = document_factory(normalized_headings={SectionType.METHODS: "too short"})
    profile = SectionProfiler().profile(document, classification_factory(document_type=DocumentType.PROTOCOL))
    assert 0.0 < profile.section_completeness[SectionType.METHODS] < 1.0


def test_substantial_section_gets_full_completeness(document_factory, classification_factory):
    document = document_factory(normalized_headings={SectionType.METHODS: "word " * 30})
    profile = SectionProfiler().profile(document, classification_factory(document_type=DocumentType.PROTOCOL))
    assert profile.section_completeness[SectionType.METHODS] == 1.0


def test_missing_recommended_section_gets_zero_completeness(document_factory, classification_factory):
    document = document_factory(normalized_headings={})
    profile = SectionProfiler().profile(document, classification_factory(document_type=DocumentType.PROTOCOL))
    assert profile.section_completeness[SectionType.METHODS] == 0.0


def test_no_recommendation_for_document_type_with_no_structural_signature(document_factory, classification_factory):
    document = document_factory(normalized_headings={SectionType.DISCUSSION: "word " * 30})
    profile = SectionProfiler().profile(document, classification_factory(document_type=DocumentType.EDITORIAL))
    assert profile.recommended_sections == []
    assert profile.missing_sections == []


def test_strong_heading_pattern_yields_high_section_confidence(document_factory, classification_factory):
    structure = DocumentStructure(
        normalized_headings={SectionType.METHODS: "word " * 30},
        section_types={"1. Methods": SectionType.METHODS},
        heading_types={"1. Methods": HeadingType.NUMBERED},
    )
    document = document_factory()
    document.structure = structure

    profile = SectionProfiler().profile(document, classification_factory())
    assert profile.section_confidence[SectionType.METHODS] == 1.0


def test_bare_heading_pattern_yields_lower_section_confidence(document_factory, classification_factory):
    structure = DocumentStructure(
        normalized_headings={SectionType.METHODS: "word " * 30},
        section_types={"Methods": SectionType.METHODS},
        heading_types={"Methods": HeadingType.BARE},
    )
    document = document_factory()
    document.structure = structure

    profile = SectionProfiler().profile(document, classification_factory())
    assert profile.section_confidence[SectionType.METHODS] == 0.6
