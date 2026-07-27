import pytest

from backend.medical_understanding.config import MedicalUnderstandingConfig
from backend.medical_understanding.models import ConfidenceScore, MedicalUnderstanding
from backend.medical_understanding.validators import require_valid_inputs, validate_inputs, validate_output


def test_require_valid_inputs_raises_on_wrong_document_type(classification_factory, context_factory):
    with pytest.raises(TypeError, match="ProcessedDocument"):
        require_valid_inputs({"not": "a document"}, classification_factory(), context_factory())


def test_require_valid_inputs_raises_on_wrong_classification_type(context_factory, pdf_factory):
    from backend.medical_understanding.conftest import process_pdf

    document = process_pdf(pdf_factory(["Some content."]))
    with pytest.raises(TypeError, match="ClassificationResult"):
        require_valid_inputs(document, {"not": "a classification"}, context_factory())


def test_require_valid_inputs_raises_on_wrong_context_type(classification_factory, pdf_factory):
    from backend.medical_understanding.conftest import process_pdf

    document = process_pdf(pdf_factory(["Some content."]))
    with pytest.raises(TypeError, match="AnalysisContext"):
        require_valid_inputs(document, classification_factory(), {"not": "a context"})


def test_validate_inputs_warns_on_empty_text(classification_factory, context_factory, pdf_factory):
    from backend.medical_understanding.conftest import process_pdf

    document = process_pdf(pdf_factory(["Untitled"]))
    document.full_text = ""
    warnings = validate_inputs(document, classification_factory(), context_factory())
    assert any("no extractable text" in w for w in warnings)


def test_validate_inputs_warns_on_low_reliability(classification_factory, pdf_factory):
    from backend.medical_understanding.conftest import make_context, process_pdf

    document = process_pdf(pdf_factory(["Some content."]))
    context = make_context()
    context.quality_profile.reliability_score = 0.1
    warnings = validate_inputs(document, classification_factory(), context)
    assert any("reliability is low" in w for w in warnings)


def test_validate_output_warns_when_entity_limit_reached():
    understanding = MedicalUnderstanding(
        clinical_entities=[object()] * 5, confidence=ConfidenceScore(overall=0.5, components={}, formula="")
    )
    config = MedicalUnderstandingConfig(max_entities=5)
    warnings = validate_output(understanding, config)
    assert any("entity count reached" in w for w in warnings)


def test_validate_output_warns_on_out_of_range_confidence():
    understanding = MedicalUnderstanding(confidence=ConfidenceScore(overall=1.5, components={}, formula=""))
    warnings = validate_output(understanding, MedicalUnderstandingConfig())
    assert any("outside the valid" in w for w in warnings)


def test_validate_output_no_warnings_for_healthy_result():
    understanding = MedicalUnderstanding(confidence=ConfidenceScore(overall=0.7, components={}, formula=""))
    assert validate_output(understanding, MedicalUnderstandingConfig()) == []
