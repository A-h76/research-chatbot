from backend.classification.pass2.enums import StudyDesign
from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.extractors.study_characteristics import StudyCharacteristicsExtractor


def _extract(pdf_factory, text, classification):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    return StudyCharacteristicsExtractor().extract(index, classification, None, EntityRegistry())


def test_reuses_classification_study_design(pdf_factory, classification_factory):
    classification = classification_factory(study_design=StudyDesign.RCT)
    result = _extract(pdf_factory, "Methods\nSome methods text.\n", classification)
    assert result.get("study_characteristics").study_design == StudyDesign.RCT


def test_detects_blinding_and_arms(pdf_factory, classification_factory):
    text = "Methods\nThis was a double-blind, 2-arm design.\n"
    result = _extract(pdf_factory, text, classification_factory())
    sc = result.get("study_characteristics")
    assert sc.blinding == "double-blind"
    assert sc.number_of_arms == 2


def test_detects_multicenter_and_sites(pdf_factory, classification_factory):
    text = "Methods\nThis was a multicenter trial conducted across 5 sites.\n"
    result = _extract(pdf_factory, text, classification_factory())
    sc = result.get("study_characteristics")
    assert sc.multicenter is True
    assert sc.number_of_sites == 5


def test_no_multicenter_mention_leaves_field_unknown(pdf_factory, classification_factory):
    text = "Methods\nPatients were randomly assigned.\n"
    result = _extract(pdf_factory, text, classification_factory())
    assert result.get("study_characteristics").multicenter is None
