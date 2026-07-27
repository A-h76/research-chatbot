"""Tests for backend/classification/pass1/__init__.py's classify_document()
orchestration.

Run: pytest backend/classification/pass1/test_pipeline.py -v
"""

import os

import fitz

from backend.classification.pass1 import DocumentUnderstanding, classify_document
from backend.processing import process_pdf


def test_classify_document_assembles_all_three_stages(make_document):
    doc = make_document(
        venue="The Lancet",
        abstract="We conducted a randomized controlled trial in patients treated at a hospital.",
        has_methods=True,
        has_results=True,
        has_discussion=True,
    )

    understanding = classify_document(doc)

    assert isinstance(understanding, DocumentUnderstanding)
    assert understanding.domain == "medical"
    assert understanding.document_type == "research_article"
    assert understanding.publication_type == "journal_article"
    assert 0.0 <= understanding.confidence <= 1.0
    assert understanding.reasoning
    assert understanding.matched_features


def test_classify_document_confidence_is_mean_of_the_three_primary_scores(make_document):
    doc = make_document(venue="The Lancet", abstract="patient clinical treatment hospital")

    understanding = classify_document(doc)

    domain_conf = dict(understanding.domains)[understanding.domain]
    type_conf = dict(understanding.document_types)[understanding.document_type]
    # publication_type has no ...s list to look confidence up in — recompute
    # by classifying it the same way classify_document() itself does.
    from backend.classification.pass1.publication import PublicationTypeClassifier

    pub_result = PublicationTypeClassifier().classify(doc, document_type=understanding.document_type)

    expected = (domain_conf + type_conf + pub_result.confidence) / 3
    assert understanding.confidence == expected


def test_classify_document_reasoning_covers_all_three_stages(make_document):
    doc = make_document(
        venue="The Lancet",
        abstract="We conducted a randomized controlled trial in patients treated at a hospital.",
        has_methods=True,
        has_results=True,
        has_discussion=True,
    )
    understanding = classify_document(doc)

    joined = " | ".join(understanding.reasoning)
    assert "medical" in joined  # domain stage
    assert "structural feature" in joined  # document_type stage
    assert "venue matches known journal_article venue" in joined  # publication_type stage


def test_classify_document_matched_features_merged_across_stages(make_document):
    doc = make_document(venue="The Lancet", abstract="patient clinical treatment")
    understanding = classify_document(doc)
    assert "medical" in understanding.matched_features
    assert "journal_article" in understanding.matched_features


def test_classify_document_with_no_signals_falls_back_to_other_everywhere(make_document):
    doc = make_document(abstract="Completely generic prose with no distinguishing signal.")
    understanding = classify_document(doc)
    assert understanding.domain == "other"
    assert understanding.document_type == "other"
    assert understanding.publication_type == "other"
    assert understanding.confidence == 0.0


def test_classify_document_end_to_end_from_a_real_pdf(tmp_path):
    # Full stack: a real PDF -> process_pdf() -> classify_document(),
    # proving the two packages' dataclass shapes actually compose.
    doc_pdf = fitz.open()
    p1 = doc_pdf.new_page()
    for i, line in enumerate(
        [
            "A Randomized Controlled Trial of a New Drug for Hypertension",
            "Jane Doe, John Smith",
            "Abstract",
            "We conducted a randomized controlled trial in patients with hypertension treated at a hospital.",
        ]
    ):
        p1.insert_text((72, 72 + i * 20), line)
    p2 = doc_pdf.new_page()
    p2.insert_text((72, 72), "Methods")
    p2.insert_text((72, 100), "We recruited patients under a randomized protocol.")
    p3 = doc_pdf.new_page()
    p3.insert_text((72, 72), "Results")
    p3.insert_text((72, 100), "Blood pressure was significantly reduced in the treatment group.")
    p4 = doc_pdf.new_page()
    p4.insert_text((72, 72), "Discussion")
    p4.insert_text((72, 100), "This confirms efficacy of the drug for treating hypertension.")
    doc_pdf.set_metadata({"title": "A Randomized Controlled Trial of a New Drug for Hypertension"})
    path = os.path.join(tmp_path, "sample.pdf")
    doc_pdf.save(path)
    doc_pdf.close()

    processed = process_pdf(path, doc_id="1", name="sample.pdf")
    understanding = classify_document(processed)

    assert understanding.domain == "medical"
    assert understanding.document_type == "research_article"
