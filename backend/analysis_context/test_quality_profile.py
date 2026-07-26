from backend.analysis_context.quality_profile import QualityProfiler
from backend.document_understanding.enums import QualityLevel


def test_reliability_blends_document_and_classification_confidence(document_factory, classification_factory):
    document = document_factory(quality_confidence=0.8)
    classification = classification_factory(
        document_type_confidence=0.8,
        domain_confidence=0.8,
        study_design_confidence=0.8,
        reporting_guideline_confidence=0.8,
    )
    profile = QualityProfiler().profile(document, classification)
    assert profile.input_document_quality == 0.8
    assert profile.input_classification_confidence == 0.8
    assert profile.reliability_score == 0.8
    assert profile.reliability_level == QualityLevel.from_score(0.8)


def test_low_document_quality_adds_a_caveat(document_factory, classification_factory):
    document = document_factory(quality_confidence=0.1)
    profile = QualityProfiler().profile(document, classification_factory())
    assert any("source document quality is low" in c for c in profile.caveats)


def test_low_classification_confidence_adds_a_caveat(document_factory, classification_factory):
    classification = classification_factory(
        document_type_confidence=0.1,
        domain_confidence=0.1,
        study_design_confidence=0.1,
        reporting_guideline_confidence=0.1,
    )
    profile = QualityProfiler().profile(document_factory(quality_confidence=0.9), classification)
    assert any("classification confidence is low" in c for c in profile.caveats)


def test_document_quality_warnings_and_errors_are_carried_into_caveats(document_factory, classification_factory):
    document = document_factory(quality_warnings=["no extractable text found"])
    profile = QualityProfiler().profile(document, classification_factory())
    assert "no extractable text found" in profile.caveats
