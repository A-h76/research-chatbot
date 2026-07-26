from backend.analysis_context.document_profile import DocumentProfiler
from backend.analysis_context.enums import AudienceType, ComplexityLevel
from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain


def test_medicine_clinical_guideline_gets_clinical_audience(document_factory, classification_factory):
    classification = classification_factory(
        document_type=DocumentType.CLINICAL_GUIDELINE, domain=ScientificDomain.MEDICINE
    )
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.intended_audience == AudienceType.CLINICAL


def test_medicine_research_article_gets_research_audience(document_factory, classification_factory):
    classification = classification_factory(
        document_type=DocumentType.RESEARCH_ARTICLE, domain=ScientificDomain.MEDICINE
    )
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.intended_audience == AudienceType.RESEARCH


def test_computer_science_gets_technical_audience(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.COMPUTER_SCIENCE)
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.intended_audience == AudienceType.TECHNICAL


def test_unknown_domain_gets_unknown_audience(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.UNKNOWN)
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.intended_audience == AudienceType.UNKNOWN


def test_complexity_scales_with_word_count(document_factory, classification_factory):
    classification = classification_factory()
    simple = DocumentProfiler().profile(document_factory(word_count=500, reference_count=0), classification)
    complex_doc = DocumentProfiler().profile(document_factory(word_count=8000, reference_count=0), classification)
    assert simple.complexity_level == ComplexityLevel.SIMPLE
    assert complex_doc.complexity_level == ComplexityLevel.COMPLEX


def test_high_reference_count_bumps_complexity_up_one_level(document_factory, classification_factory):
    classification = classification_factory()
    few_refs = DocumentProfiler().profile(document_factory(word_count=500, reference_count=0), classification)
    many_refs = DocumentProfiler().profile(document_factory(word_count=500, reference_count=100), classification)
    assert few_refs.complexity_level == ComplexityLevel.SIMPLE
    assert many_refs.complexity_level == ComplexityLevel.MODERATE


def test_zero_word_count_is_unknown_complexity(document_factory, classification_factory):
    profile = DocumentProfiler().profile(document_factory(word_count=0), classification_factory())
    assert profile.complexity_level == ComplexityLevel.UNKNOWN


def test_reporting_guideline_unknown_becomes_none(document_factory, classification_factory):
    classification = classification_factory(reporting_guideline=ReportingGuideline.UNKNOWN)
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.reporting_guideline is None


def test_reporting_guideline_none_member_is_preserved_not_collapsed(document_factory, classification_factory):
    classification = classification_factory(reporting_guideline=ReportingGuideline.NONE)
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.reporting_guideline == ReportingGuideline.NONE


def test_confidence_blends_the_three_core_classification_decisions(document_factory, classification_factory):
    classification = classification_factory(
        document_type_confidence=0.9, domain_confidence=0.6, study_design_confidence=0.3
    )
    profile = DocumentProfiler().profile(document_factory(), classification)
    assert profile.confidence == (0.9 + 0.6 + 0.3) / 3
