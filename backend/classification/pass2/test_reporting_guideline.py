from backend.classification.pass2.enums import DocumentType, ReportingGuideline, StudyDesign
from backend.classification.pass2.reporting_guideline import ReportingGuidelineDetector


def test_detects_consort_from_keywords_alone(document_factory):
    document = document_factory(full_text="This trial follows the consort statement and consort checklist.")
    decision = ReportingGuidelineDetector().detect(document)
    assert decision.label == ReportingGuideline.CONSORT


def test_study_design_corroborates_consort_even_without_keyword(document_factory):
    document = document_factory(full_text="No checklist name appears anywhere in this document at all.")
    decision = ReportingGuidelineDetector().detect(document, study_design=StudyDesign.RCT)
    assert decision.label == ReportingGuideline.CONSORT
    assert decision.evidence


def test_document_type_corroborates_care_for_case_reports(document_factory):
    document = document_factory(full_text="No checklist name appears anywhere in this document at all.")
    decision = ReportingGuidelineDetector().detect(document, document_type=DocumentType.CASE_REPORT)
    assert decision.label == ReportingGuideline.CARE


def test_keyword_and_corroboration_combine_for_higher_confidence(document_factory):
    document = document_factory(full_text="This trial follows the consort statement.")
    keyword_only = ReportingGuidelineDetector().detect(document)
    with_corroboration = ReportingGuidelineDetector().detect(document, study_design=StudyDesign.RCT)
    assert with_corroboration.confidence >= keyword_only.confidence


def test_no_signal_falls_back_to_unknown(document_factory):
    document = document_factory(full_text="A generic sentence with no reporting guideline markers.")
    decision = ReportingGuidelineDetector().detect(document)
    assert decision.label == ReportingGuideline.UNKNOWN
