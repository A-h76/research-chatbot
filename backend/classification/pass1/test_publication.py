"""Tests for backend/classification/pass1/publication.py.

Run: pytest backend/classification/pass1/test_publication.py -v
"""

from backend.classification.pass1.publication import PublicationTypeClassifier

classifier = PublicationTypeClassifier()


def test_classifies_conference_paper_by_venue(make_document):
    doc = make_document(venue="Proceedings of NeurIPS 2024")
    result = classifier.classify(doc)
    assert result.publication_type == "conference_paper"
    assert result.confidence > 0.0


def test_classifies_journal_article_by_venue(make_document):
    doc = make_document(venue="Journal of Widget Studies")
    result = classifier.classify(doc)
    assert result.publication_type == "journal_article"


def test_classifies_preprint_by_content_keyword(make_document):
    doc = make_document(abstract="This preprint has not yet been peer reviewed. Posted on arXiv.")
    result = classifier.classify(doc)
    assert result.publication_type == "preprint"


def test_classifies_thesis_by_content_keyword(make_document):
    doc = make_document(
        abstract="A thesis submitted in partial fulfillment of the requirements for the degree of Doctor of Philosophy."
    )
    result = classifier.classify(doc)
    assert result.publication_type == "thesis"


def test_document_type_signal_used_when_no_venue_or_keyword_present(make_document):
    doc = make_document(abstract="Nothing venue- or keyword-distinctive here.")
    result = classifier.classify(doc, document_type="preprint")
    assert result.publication_type == "preprint"
    assert any("document_type classified as 'preprint'" in r for r in result.reasoning)


def test_venue_signal_outweighs_document_type_signal(make_document):
    # document_type says "thesis", but a clear conference venue should win
    # (venue weighted higher than the document_type crosswalk signal).
    doc = make_document(venue="Proceedings of ICML 2024")
    result = classifier.classify(doc, document_type="thesis")
    assert result.publication_type == "conference_paper"


def test_document_type_with_no_publication_mapping_contributes_nothing(make_document):
    # "research_article" isn't in DOCUMENT_TYPE_TO_PUBLICATION_TYPE — should
    # behave identically to passing the default "other".
    doc = make_document(venue="Journal of Widget Studies")
    result = classifier.classify(doc, document_type="research_article")
    assert result.publication_type == "journal_article"


def test_no_signal_falls_back_to_other(make_document):
    doc = make_document(abstract="Nothing distinctive at all.")
    result = classifier.classify(doc)
    assert result.publication_type == "other"
    assert result.confidence == 0.0


def test_matched_features_and_reasoning_populated(make_document):
    doc = make_document(venue="Proceedings of NeurIPS 2024")
    result = classifier.classify(doc)
    assert "conference_paper" in result.matched_features
    assert result.reasoning
