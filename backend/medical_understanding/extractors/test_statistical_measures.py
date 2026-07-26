from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.document_index import build_document_index
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.enums import StatisticalMeasureType
from backend.medical_understanding.extractors.statistical_measures import StatisticalMeasuresExtractor


def _extract(pdf_factory, text):
    document = process_pdf(pdf_factory([text]))
    index = build_document_index(document)
    return StatisticalMeasuresExtractor().extract(index, None, None, EntityRegistry())


def test_detects_p_value(pdf_factory):
    result = _extract(pdf_factory, "Results\nThe result was significant, p=0.002.\n")
    measures = result.get("statistical_measures")
    p_values = [m for m in measures if m.measure_type == StatisticalMeasureType.P_VALUE]
    assert p_values and p_values[0].value == "p=0.002"


def test_detects_confidence_interval(pdf_factory):
    result = _extract(pdf_factory, "Results\nHazard ratio 1.45, 95% CI 1.02-2.07.\n")
    measures = result.get("statistical_measures")
    assert any(m.measure_type == StatisticalMeasureType.CONFIDENCE_INTERVAL for m in measures)
    assert any(m.measure_type == StatisticalMeasureType.HAZARD_RATIO for m in measures)


def test_detects_odds_ratio_and_relative_risk(pdf_factory):
    result = _extract(pdf_factory, "Results\nOR 2.1 was reported. RR 1.8 was also noted.\n")
    types = {m.measure_type for m in result.get("statistical_measures")}
    assert StatisticalMeasureType.ODDS_RATIO in types
    assert StatisticalMeasureType.RELATIVE_RISK in types


def test_detects_mean_difference_and_effect_size(pdf_factory):
    result = _extract(pdf_factory, "Results\nMean difference was notable. Effect size was moderate.\n")
    types = {m.measure_type for m in result.get("statistical_measures")}
    assert StatisticalMeasureType.MEAN_DIFFERENCE in types
    assert StatisticalMeasureType.EFFECT_SIZE in types


def test_no_statistics_yields_empty_list(pdf_factory):
    result = _extract(pdf_factory, "Results\nA generic sentence with no statistics.\n")
    assert result.get("statistical_measures") == []
