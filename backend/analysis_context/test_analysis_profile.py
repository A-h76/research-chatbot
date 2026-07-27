from backend.analysis_context.analysis_profile import AnalysisProfiler
from backend.analysis_context.enums import AnalysisType, ReadinessLevel
from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign
from backend.document_understanding.enums import SectionType


def test_rct_yields_statistical_and_bias_analysis_types(document_factory, classification_factory):
    classification = classification_factory(study_design=StudyDesign.RCT, domain=ScientificDomain.MEDICINE)
    profile = AnalysisProfiler().profile(document_factory(), classification)
    assert AnalysisType.STATISTICAL_REVIEW in profile.analysis_types
    assert AnalysisType.BIAS_ASSESSMENT in profile.analysis_types
    assert AnalysisType.CLINICAL_INTERPRETATION in profile.analysis_types  # from domain=medicine


def test_unknown_study_design_and_non_medicine_domain_falls_back_to_unknown(document_factory, classification_factory):
    classification = classification_factory(study_design=StudyDesign.UNKNOWN, domain=ScientificDomain.PHYSICS)
    profile = AnalysisProfiler().profile(document_factory(), classification)
    assert profile.analysis_types == [AnalysisType.UNKNOWN]


def test_high_confidence_types_are_required_not_suggested(document_factory, classification_factory):
    classification = classification_factory(study_design_confidence=0.9, domain_confidence=0.9)
    profile = AnalysisProfiler().profile(document_factory(), classification)
    assert profile.required_modules
    assert profile.suggested_modules == []


def test_low_confidence_types_are_suggested_not_required(document_factory, classification_factory):
    classification = classification_factory(study_design_confidence=0.1, domain_confidence=0.1)
    profile = AnalysisProfiler().profile(document_factory(), classification)
    assert profile.required_modules == []
    assert profile.suggested_modules


def test_all_recommended_sections_present_is_fully_ready(document_factory, classification_factory):
    document = document_factory(
        normalized_headings={
            SectionType.METHODS: "x",
            SectionType.RESULTS: "x",
            SectionType.DISCUSSION: "x",
        }
    )
    classification = classification_factory(document_type=DocumentType.RESEARCH_ARTICLE, document_type_confidence=0.9)
    profile = AnalysisProfiler().profile(document, classification)
    assert profile.readiness_level == ReadinessLevel.FULLY_READY


def test_missing_all_recommended_sections_reports_limitations(document_factory, classification_factory):
    document = document_factory(normalized_headings={})
    classification = classification_factory(document_type=DocumentType.RESEARCH_ARTICLE)
    profile = AnalysisProfiler().profile(document, classification)
    assert any("missing expected section" in limitation for limitation in profile.limitations)


def test_unknown_study_design_is_a_limitation(document_factory, classification_factory):
    classification = classification_factory(study_design=StudyDesign.UNKNOWN)
    profile = AnalysisProfiler().profile(document_factory(), classification)
    assert "study design could not be confidently classified" in profile.limitations
