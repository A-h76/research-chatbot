from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.extractors.temporal_data import TemporalDataExtractor


def _extract(pdf_factory, text):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    return TemporalDataExtractor().extract(index, None, None, EntityRegistry())


def test_detects_study_duration_and_follow_up(pdf_factory):
    text = "Methods\nStudy duration of 24 weeks.\nFollow-up period of 52 weeks.\n"
    result = _extract(pdf_factory, text)
    temporal_data = result.get("temporal_data")
    assert temporal_data.study_duration == "Study duration of 24 weeks"
    assert temporal_data.follow_up_period == "Follow-up period of 52 weeks"


def test_detects_enrollment_period(pdf_factory):
    text = "Methods\nEnrolled between Jan 2020 and Mar 2021.\n"
    result = _extract(pdf_factory, text)
    assert "Enrolled between" in result.get("temporal_data").enrollment_period


def test_detects_key_timepoints(pdf_factory):
    text = "Results\nOutcomes were assessed at 12 weeks and at 24 weeks.\n"
    result = _extract(pdf_factory, text)
    assert result.get("temporal_data").key_timepoints


def test_nothing_found_yields_zero_confidence(pdf_factory):
    text = "Methods\nA generic sentence with no temporal markers.\n"
    result = _extract(pdf_factory, text)
    temporal_data = result.get("temporal_data")
    assert temporal_data.confidence == 0.0
    assert temporal_data.study_duration is None
