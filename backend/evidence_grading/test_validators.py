import pytest

from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.models import EvidenceGrades
from backend.evidence_grading.validators import require_valid_inputs, validate_inputs, validate_output


def test_require_valid_inputs_raises_on_wrong_type(classification_factory, context_factory, medical_factory):
    with pytest.raises(TypeError):
        require_valid_inputs("not a document", classification_factory(), context_factory(), medical_factory())


def test_require_valid_inputs_accepts_real_types(pdf_factory, classification_factory, context_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Methods\nPatients were randomized."]))
    require_valid_inputs(document, classification_factory(), context_factory(), medical_factory())


def test_validate_inputs_warns_on_skipped_medical(pdf_factory, classification_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Methods\nPatients were randomized."]))
    warnings = validate_inputs(document, classification_factory(), medical_factory(skipped=True))
    assert any("medical understanding was itself skipped" in w for w in warnings)


def test_validate_inputs_warns_on_low_study_design_confidence(pdf_factory, classification_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Methods\nPatients were randomized."]))
    classification = classification_factory(study_design=classification_factory().study_design.label)
    classification.study_design.confidence = 0.1
    warnings = validate_inputs(document, classification, medical_factory())
    assert any("study_design classification confidence is low" in w for w in warnings)


def test_validate_output_warns_when_outcome_limit_reached():
    config = EvidenceGradingConfig(max_outcomes=1)
    grades = EvidenceGrades(outcome_grades={"a": None, "b": None})
    warnings = validate_output(grades, config)
    assert any("outcome grade count reached" in w for w in warnings)


def test_validate_output_warns_on_confidence_out_of_range():
    from backend.evidence_grading.models import ConfidenceScore

    config = EvidenceGradingConfig()
    grades = EvidenceGrades(confidence=ConfidenceScore(overall=1.5, components={}, formula=""))
    warnings = validate_output(grades, config)
    assert any("outside the valid" in w for w in warnings)
