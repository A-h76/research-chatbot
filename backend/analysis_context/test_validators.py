import pytest

from backend.analysis_context.validators import require_valid_inputs, validate_inputs


def test_require_valid_inputs_raises_on_wrong_document_type(classification_factory):
    with pytest.raises(TypeError, match="ProcessedDocument"):
        require_valid_inputs({"not": "a document"}, classification_factory())


def test_require_valid_inputs_raises_on_wrong_classification_type(document_factory):
    with pytest.raises(TypeError, match="ClassificationResult"):
        require_valid_inputs(document_factory(), {"not": "a classification"})


def test_require_valid_inputs_accepts_real_types(document_factory, classification_factory):
    require_valid_inputs(document_factory(), classification_factory())


def test_validate_inputs_warns_on_empty_text(document_factory, classification_factory):
    warnings = validate_inputs(document_factory(full_text=""), classification_factory())
    assert any("no extractable text" in w for w in warnings)


def test_validate_inputs_warns_on_low_confidence_decisions(document_factory, classification_factory):
    classification = classification_factory(domain_confidence=0.1)
    warnings = validate_inputs(document_factory(), classification)
    assert any("domain confidence is low" in w for w in warnings)


def test_validate_inputs_no_warnings_for_healthy_inputs(document_factory, classification_factory):
    assert validate_inputs(document_factory(), classification_factory()) == []
