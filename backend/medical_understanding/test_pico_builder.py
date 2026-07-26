from backend.medical_understanding.models import Comparator, Intervention, Outcome, Population
from backend.medical_understanding.pico_builder import build_pico


def test_assembles_pico_from_extracted_lists():
    population = Population(sample_size=100, confidence=0.7)
    interventions = [Intervention(name="metformin", confidence=0.8)]
    comparators = [Comparator(name="placebo", is_placebo=True, confidence=0.7)]
    outcomes = [Outcome(name="HbA1c change", confidence=0.6)]

    pico = build_pico([population], interventions, comparators, outcomes)

    assert pico.population is population
    assert pico.interventions == interventions
    assert pico.comparators == comparators
    assert pico.outcomes == outcomes


def test_population_is_none_when_list_empty():
    pico = build_pico([], [], [], [])
    assert pico.population is None
    assert pico.confidence == 0.0


def test_confidence_is_mean_of_all_component_confidences():
    population = Population(confidence=0.4)
    interventions = [Intervention(name="a", confidence=0.6)]
    comparators = [Comparator(name="b", confidence=0.8)]
    outcomes = [Outcome(name="c", confidence=1.0)]

    pico = build_pico([population], interventions, comparators, outcomes)
    assert pico.confidence == (0.4 + 0.6 + 0.8 + 1.0) / 4


def test_confidence_without_population_still_averages_the_rest():
    interventions = [Intervention(name="a", confidence=0.5)]
    pico = build_pico([], interventions, [], [])
    assert pico.confidence == 0.5
