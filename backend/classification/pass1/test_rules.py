"""Tests for backend/classification/pass1/rules.py.

Run: pytest backend/classification/pass1/test_rules.py -v
"""

from backend.classification.pass1.rules import (
    SignalMatch,
    combine_signals,
    match_keywords,
    match_structural_features,
    match_venue,
)

_KEYWORDS = {
    "medical": ["patient", "clinical", "treatment", "hospital"],
    "computer_science": ["algorithm", "neural network"],
}


def test_match_keywords_scores_by_fraction_matched():
    result = match_keywords("The patient received clinical treatment.", _KEYWORDS)
    assert result["medical"].weight == 3 / 4
    assert set(result["medical"].matched_terms) == {"patient", "clinical", "treatment"}
    assert "computer_science" not in result


def test_match_keywords_case_insensitive():
    result = match_keywords("PATIENT CLINICAL", _KEYWORDS)
    assert "medical" in result


def test_match_keywords_empty_text_returns_empty():
    assert match_keywords("", _KEYWORDS) == {}
    assert match_keywords(None, _KEYWORDS) == {}  # type: ignore[arg-type]


def test_match_keywords_no_matches_omits_label():
    result = match_keywords("completely unrelated prose", _KEYWORDS)
    assert result == {}


_VENUES = {
    "medical": ["lancet", "nejm"],
    "computer_science": ["neurips", "icml"],
}


def test_match_venue_full_confidence_on_any_match():
    result = match_venue("The Lancet", _VENUES)
    assert result["medical"].weight == 1.0
    assert result["medical"].matched_terms == ["lancet"]


def test_match_venue_empty_venue_returns_empty():
    assert match_venue("", _VENUES) == {}
    assert match_venue(None, _VENUES) == {}  # type: ignore[arg-type]


def test_match_venue_no_match_returns_empty():
    assert match_venue("Some Unrelated Publisher", _VENUES) == {}


_STRUCTURAL = {
    "research_article": ("has_methods", "has_results", "has_discussion"),
    "review": ("has_abstract", "has_discussion"),
}


def test_match_structural_features_scores_by_fraction_present():
    result = match_structural_features({"has_methods", "has_results"}, _STRUCTURAL)
    assert result["research_article"].weight == 2 / 3
    assert set(result["research_article"].matched_terms) == {"has_methods", "has_results"}
    assert "review" not in result  # neither of review's own two features are present


def test_match_structural_features_none_present_omits_all():
    assert match_structural_features(set(), _STRUCTURAL) == {}


def test_combine_signals_weighted_average_across_sources():
    strong = {"a": SignalMatch("a", 1.0, ["x"], "strong evidence")}
    weak = {"a": SignalMatch("a", 0.5, ["y"], "weak evidence")}

    ranked, reasoning, matched_features = combine_signals((strong, 2.0), (weak, 1.0))

    # (1.0 * 2.0 + 0.5 * 1.0) / (2.0 + 1.0) = 2.5 / 3.0
    assert ranked == [("a", 2.5 / 3.0)]
    assert len(reasoning) == 2
    assert matched_features["a"] == ["x", "y"]


def test_combine_signals_label_missing_from_a_source_scores_as_zero_for_that_source():
    only_in_one = {"a": SignalMatch("a", 1.0, ["x"], "found in source 1")}
    empty_source: dict[str, SignalMatch] = {}

    ranked, _, _ = combine_signals((only_in_one, 1.0), (empty_source, 1.0))

    # (1.0*1.0 + 0) / 2.0 = 0.5, not 1.0 — the silent source still counts
    # toward total_weight even though it found nothing.
    assert ranked == [("a", 0.5)]


def test_combine_signals_ranks_descending_by_confidence():
    signals = {
        "high": SignalMatch("high", 1.0, [], "r"),
        "low": SignalMatch("low", 0.2, [], "r"),
    }
    ranked, _, _ = combine_signals((signals, 1.0))
    assert [label for label, _ in ranked] == ["high", "low"]


def test_combine_signals_no_sources_returns_empty():
    assert combine_signals() == ([], [], {})


def test_combine_signals_all_sources_empty_returns_empty():
    assert combine_signals(({}, 1.0), ({}, 2.0)) == ([], [], {})
