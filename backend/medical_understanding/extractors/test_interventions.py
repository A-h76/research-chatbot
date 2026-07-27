from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.extractors.clinical_entities import ClinicalEntityExtractor
from backend.medical_understanding.extractors.interventions import InterventionExtractor


def _extract(pdf_factory, text):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    registry = EntityRegistry()
    ClinicalEntityExtractor().extract(index, None, None, registry)
    return InterventionExtractor().extract(index, None, None, registry)


def test_promotes_drugs_mentioned_with_administration_marker(pdf_factory):
    text = "Methods\nPatients received metformin or placebo for treatment.\n"
    result = _extract(pdf_factory, text)
    names = {(i.name, i.intervention_type.value) for i in result.get("interventions")}
    assert ("metformin", "drug") in names
    assert ("placebo", "drug") in names


def test_finds_treated_with_marker_in_results_section(pdf_factory):
    text = "Results\nPatients treated with metformin showed improvement.\n"
    result = _extract(pdf_factory, text)
    names = [i.name for i in result.get("interventions")]
    assert "metformin" in names


def test_finds_randomly_assigned_to_marker(pdf_factory):
    text = "Methods\nPatients were randomly assigned to receive metformin.\n"
    result = _extract(pdf_factory, text)
    names = [i.name for i in result.get("interventions")]
    assert "metformin" in names


def test_no_marker_yields_no_interventions(pdf_factory):
    text = "Methods\nMetformin was mentioned without an administration marker nearby elsewhere.\n"
    result = _extract(pdf_factory, text)
    assert result.get("interventions") == []


def test_no_drug_entities_yields_no_interventions_even_with_marker(pdf_factory):
    text = "Methods\nPatients received standard care for their condition.\n"
    result = _extract(pdf_factory, text)
    assert result.get("interventions") == []
