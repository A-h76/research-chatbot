from backend.classification.pass2.document_type import DocumentTypeDetector
from backend.classification.pass2.enums import DocumentType
from backend.document_understanding.enums import SectionType


def test_detects_research_article_from_keywords_and_structure(document_factory):
    document = document_factory(
        full_text="We conducted a study. Our results show statistically significant improvement. Sample size was 100.",
        normalized_headings={
            SectionType.METHODS: "methods text",
            SectionType.RESULTS: "results text",
            SectionType.DISCUSSION: "discussion text",
        },
    )
    decision = DocumentTypeDetector().detect(document)
    assert decision.label == DocumentType.RESEARCH_ARTICLE
    assert decision.confidence > 0.3
    assert decision.evidence


def test_detects_case_report_from_keywords_alone(document_factory):
    document = document_factory(
        full_text="We describe a case of a patient presented with an unusual case report. Case series follows."
    )
    decision = DocumentTypeDetector().detect(document)
    assert decision.label == DocumentType.CASE_REPORT


def test_detects_systematic_review(document_factory):
    document = document_factory(
        full_text=(
            "This systematic review follows prisma guidance. Our search strategy and study selection process "
            "included studies from multiple databases with a risk of bias assessment."
        )
    )
    decision = DocumentTypeDetector().detect(document)
    assert decision.label == DocumentType.SYSTEMATIC_REVIEW


def test_no_signal_falls_back_to_unknown(document_factory):
    document = document_factory(full_text="A completely generic piece of text with no distinguishing markers.")
    decision = DocumentTypeDetector().detect(document)
    assert decision.label == DocumentType.UNKNOWN
    assert decision.reasoning is None


def test_rank_exposes_every_candidate_not_just_the_winner(document_factory):
    document = document_factory(full_text="We conducted a case report describing a patient who presented with pain.")
    ranked, sources = DocumentTypeDetector().rank(document)
    labels = [label for label, _ in ranked]
    assert DocumentType.CASE_REPORT in labels
    assert isinstance(sources, list)
