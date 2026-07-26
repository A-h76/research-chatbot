from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.enums import ClinicalEntityType
from backend.medical_understanding.extractors.clinical_entities import ClinicalEntityExtractor


def _extract(pdf_factory, text):
    path = pdf_factory([text])
    document = process_pdf(path)
    index = build_document_index(document)
    registry = EntityRegistry()
    result = ClinicalEntityExtractor().extract(index, None, None, registry)
    return result, registry


def test_detects_conditions_drugs_and_symptoms(pdf_factory):
    text = (
        "Abstract\nPatients with diabetes and hypertension were enrolled.\n\n"
        "Methods\nMetformin and placebo were used. Fatigue was recorded.\n"
    )
    result, registry = _extract(pdf_factory, text)
    values = {(e.entity_type.value, e.value) for e in result.entities}
    assert ("condition", "diabetes mellitus") in values
    assert ("condition", "hypertension") in values
    assert ("drug", "metformin") in values
    assert ("drug", "placebo") in values
    assert ("symptom", "fatigue") in values


def test_entities_are_registered_in_the_shared_registry(pdf_factory):
    text = "Abstract\nPatients with diabetes were treated.\n"
    result, registry = _extract(pdf_factory, text)
    assert registry.get_entity("diabetes mellitus", ClinicalEntityType.CONDITION) is not None


def test_repeated_mentions_produce_one_entity_not_duplicates(pdf_factory):
    text = "Abstract\nDiabetes patients. More diabetes discussion. Diabetes again in methods.\n"
    result, registry = _extract(pdf_factory, text)
    diabetes_entities = [e for e in result.entities if e.value == "diabetes mellitus"]
    assert len(diabetes_entities) == 1


def test_no_clinical_keywords_yields_no_entities(pdf_factory):
    text = "Abstract\nThis is a generic document about nothing clinical.\n"
    result, _ = _extract(pdf_factory, text)
    assert result.entities == []


def test_entity_evidence_has_exact_character_range(pdf_factory):
    path = pdf_factory(["Abstract\nPatients with diabetes were treated.\n"])
    document = process_pdf(path)
    index = build_document_index(document)
    result = ClinicalEntityExtractor().extract(index, None, None, EntityRegistry())
    entity = next(e for e in result.entities if e.value == "diabetes mellitus")
    start, end = entity.evidence.character_range
    assert document.full_text[start:end].lower() == "diabetes"
