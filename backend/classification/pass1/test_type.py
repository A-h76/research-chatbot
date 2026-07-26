"""Tests for backend/classification/pass1/type.py.

Run: pytest backend/classification/pass1/test_type.py -v
"""

from backend.classification.pass1.type import DocumentTypeClassifier

classifier = DocumentTypeClassifier()


def test_classifies_research_article_by_structure_and_keyword(make_document):
    doc = make_document(
        abstract="We conducted a study and our results show a statistically significant effect.",
        has_methods=True,
        has_results=True,
        has_discussion=True,
    )
    result = classifier.classify(doc)
    assert result.primary_type == "research_article"


def test_classifies_case_report_by_keyword(make_document):
    doc = make_document(
        abstract="We describe a case report of a patient who presented with an unusual condition.",
        has_abstract=True,
    )
    result = classifier.classify(doc)
    assert result.primary_type == "case_report"


def test_classifies_review_by_keyword(make_document):
    doc = make_document(
        abstract="This systematic review and meta-analysis synthesizes findings across 30 studies.",
    )
    result = classifier.classify(doc)
    assert result.primary_type == "review"


def test_classifies_clinical_guideline_by_keyword(make_document):
    doc = make_document(
        abstract="This clinical practice guideline provides recommendations for treatment.",
    )
    result = classifier.classify(doc)
    assert result.primary_type == "clinical_guideline"


def test_keyword_signal_outweighs_ambiguous_structure(make_document):
    # "case report" is decisive even though the structural shape alone
    # (just has_abstract) would be ambiguous between several types.
    doc = make_document(
        abstract="Case report: a patient presented with a rare complication.",
        has_abstract=True,
    )
    result = classifier.classify(doc)
    assert result.primary_type == "case_report"


def test_no_signal_falls_back_to_other(make_document):
    doc = make_document(abstract="Nothing structurally or lexically distinctive here.")
    result = classifier.classify(doc)
    assert result.primary_type == "other"
    assert result.document_types == [("other", 0.0)]


def test_multiple_types_ranked_by_confidence(make_document):
    doc = make_document(
        abstract="We conducted a study with methods and results.",
        has_methods=True,
        has_results=True,
        has_discussion=True,
    )
    result = classifier.classify(doc)
    assert result.document_types == sorted(result.document_types, key=lambda pair: pair[1], reverse=True)
    assert result.document_types[0][0] == "research_article"


def test_matched_features_records_structural_and_keyword_evidence(make_document):
    doc = make_document(
        abstract="We conducted a study.",
        has_methods=True,
        has_results=True,
        has_discussion=True,
    )
    result = classifier.classify(doc)
    assert "we conducted" in result.matched_features["research_article"]
    assert "has_methods" in result.matched_features["research_article"]
