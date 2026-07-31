"""Integration tests for DocumentClassificationPipeline.

test_processes_a_real_processed_document is the one test in this package
that runs a real backend.document_understanding pipeline end to end
(PyMuPDF-generated PDF, no binary fixture) — everything else uses the
lightweight document_factory (see conftest.py), since pass2's own logic
never re-parses anything Phase 1.1 already computed.
"""

import fitz
import pytest

from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from backend.classification.pass2.models import ClassificationDecision
from backend.classification.pass2.pipeline import DocumentClassificationPipeline
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline


@pytest.fixture
def pipeline():
    return DocumentClassificationPipeline()


def test_processes_a_real_processed_document(tmp_path, pipeline):
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "A Randomized Controlled Trial of Something\n\n"
        "Abstract\nWe conducted a randomized controlled trial following the consort statement.\n\n"
        "Methods\nPatients were randomly assigned in this clinical trial at the hospital.\n\n"
        "Results\nStatistically significant improvement was observed.\n\n"
        "Discussion\nThese results confirm the treatment's effect on the disease.\n"
    )
    y = 72
    for line in text.splitlines():
        page.insert_text((72, y), line)
        y += 14
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()

    processed = DocumentUnderstandingPipeline().process(path)
    result = pipeline.process(processed)

    assert result.study_design.label == StudyDesign.RCT
    assert result.reporting_guideline.label == ReportingGuideline.CONSORT
    assert result.domain.label == ScientificDomain.MEDICINE
    assert result.pipeline_version
    assert result.processing_time_ms < 100
    assert result.processing_time_ms >= 0.0


def test_raises_for_non_processed_document_input(pipeline):
    with pytest.raises(TypeError):
        pipeline.process({"not": "a ProcessedDocument"})


def test_candidate_labels_are_namespaced_and_do_not_collide(document_factory, pipeline):
    document = document_factory(full_text="We survey the field in this comprehensive survey of methods.")
    result = pipeline.process(document)

    # Both DocumentType and StudyDesign have a "survey" member — the
    # namespaced keys must keep them distinct (see pipeline.py's
    # _candidate_labels() docstring).
    assert "document_type.survey" in result.candidate_labels
    assert "study_design.survey" in result.candidate_labels


def test_a_failing_detector_degrades_to_unknown_with_a_warning(document_factory):
    class _BrokenDomainDetector:
        def detect(self, document):
            raise RuntimeError("boom")

        def rank(self, document):
            raise RuntimeError("boom")

    pipeline = DocumentClassificationPipeline(domain_detector=_BrokenDomainDetector())
    document = document_factory(full_text="We conducted a case report of a patient.")

    result = pipeline.process(document)

    assert result.domain.label == ScientificDomain.UNKNOWN
    assert result.domain.confidence == 0.0
    assert any("domain detector failed" in w for w in result.warnings)
    # the other three detectors still ran normally
    assert isinstance(result.document_type, ClassificationDecision)


def test_thin_document_produces_a_validation_warning(document_factory, pipeline):
    document = document_factory(full_text="short")
    result = pipeline.process(document)
    assert any("little extractable text" in w for w in result.warnings)


def test_reporting_guideline_receives_document_type_and_study_design_corroboration(document_factory, pipeline):
    document = document_factory(
        full_text=(
            "This randomized controlled trial used a double-blind, placebo-controlled design with "
            "random allocation of participants."
        )
    )
    result = pipeline.process(document)
    assert result.study_design.label == StudyDesign.RCT
    assert result.reporting_guideline.label == ReportingGuideline.CONSORT


def test_detected_keywords_is_flat_and_deduplicated(document_factory, pipeline):
    document = document_factory(full_text="patient patient disease medicine")
    result = pipeline.process(document)
    assert result.detected_keywords.count("patient") == 1
    assert "disease" in result.detected_keywords
    assert "we conducted" not in result.detected_keywords
