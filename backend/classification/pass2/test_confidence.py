from backend.classification.pass1.rules import SignalMatch
from backend.classification.pass2.confidence import CONFIDENCE_THRESHOLD, active_sources, resolve
from backend.classification.pass2.enums import ScientificDomain


def test_resolve_returns_top_ranked_when_above_threshold():
    ranked = [(ScientificDomain.MEDICINE, 0.8), (ScientificDomain.BIOLOGY, 0.2)]
    label, confidence = resolve(ranked, ScientificDomain.UNKNOWN)
    assert label == ScientificDomain.MEDICINE
    assert confidence == 0.8


def test_resolve_falls_back_to_unknown_below_threshold():
    ranked = [(ScientificDomain.MEDICINE, CONFIDENCE_THRESHOLD - 0.01)]
    label, confidence = resolve(ranked, ScientificDomain.UNKNOWN)
    assert label == ScientificDomain.UNKNOWN
    assert confidence == CONFIDENCE_THRESHOLD - 0.01  # real score preserved, not zeroed


def test_resolve_empty_ranked_list_is_unknown_at_zero_confidence():
    label, confidence = resolve([], ScientificDomain.UNKNOWN)
    assert label == ScientificDomain.UNKNOWN
    assert confidence == 0.0


def test_active_sources_drops_empty_dicts():
    populated = {ScientificDomain.MEDICINE: SignalMatch(ScientificDomain.MEDICINE, 1.0, ["x"], "r")}
    empty: dict = {}
    result = active_sources((empty, 2.0), (populated, 1.0))
    assert result == [(populated, 1.0)]


def test_active_sources_keeps_all_when_none_are_empty():
    populated_a = {ScientificDomain.MEDICINE: SignalMatch(ScientificDomain.MEDICINE, 1.0, ["x"], "r")}
    populated_b = {ScientificDomain.BIOLOGY: SignalMatch(ScientificDomain.BIOLOGY, 1.0, ["y"], "r")}
    result = active_sources((populated_a, 2.0), (populated_b, 1.0))
    assert result == [(populated_a, 2.0), (populated_b, 1.0)]
