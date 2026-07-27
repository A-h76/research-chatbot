from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.extractors.populations import PopulationExtractor


def _extract(pdf_factory, text):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    return PopulationExtractor().extract(index, None, None, EntityRegistry())


def test_extracts_sample_size_and_age_range(pdf_factory):
    text = "Abstract\nWe enrolled 240 patients, aged 18-65 years.\n"
    result = _extract(pdf_factory, text)
    population = result.get("populations")[0]
    assert population.sample_size == 240
    assert population.age_range == "18-65 years"
    assert population.confidence > 0.0


def test_extracts_mean_age_and_sex_distribution(pdf_factory):
    text = "Abstract\nMean age of 42.3. 52% were female.\n"
    result = _extract(pdf_factory, text)
    demographic_data = result.get("demographic_data")
    assert demographic_data.mean_age == "Mean age of 42.3"
    assert demographic_data.sex_distribution == "52% were female"


def test_extracts_inclusion_and_exclusion_criteria(pdf_factory):
    text = "Methods\nInclusion criteria: adults with diagnosis. Exclusion criteria: pregnant women.\n"
    result = _extract(pdf_factory, text)
    population = result.get("populations")[0]
    assert population.inclusion_criteria == ["Inclusion criteria: adults with diagnosis."]
    assert population.exclusion_criteria == ["Exclusion criteria: pregnant women."]


def test_nothing_found_yields_zero_confidence(pdf_factory):
    text = "Abstract\nA generic sentence with no population markers.\n"
    result = _extract(pdf_factory, text)
    population = result.get("populations")[0]
    assert population.confidence == 0.0
    assert population.sample_size is None
