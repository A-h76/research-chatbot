"""Tests for backend/classification/pass1/domain.py.

Run: pytest backend/classification/pass1/test_domain.py -v
"""

from backend.classification.pass1.domain import DomainClassifier

classifier = DomainClassifier()


def test_classifies_medical_by_keyword(make_document):
    doc = make_document(
        abstract="We studied patient outcomes after clinical treatment at the hospital.",
    )
    result = classifier.classify(doc)
    assert result.primary_domain == "medical"
    assert result.domains[0][0] == "medical"
    assert result.domains[0][1] > 0.0


def test_classifies_computer_science_by_keyword(make_document):
    doc = make_document(
        abstract="We propose a new algorithm based on a neural network for benchmark dataset evaluation.",
    )
    result = classifier.classify(doc)
    assert result.primary_domain == "computer_science"


def test_classifies_by_venue_even_with_no_keyword_signal(make_document):
    doc = make_document(venue="Proceedings of NeurIPS 2024", abstract="Nothing domain-specific here at all.")
    result = classifier.classify(doc)
    assert result.primary_domain == "computer_science"
    assert any("venue" in r for r in result.reasoning)


def test_venue_signal_outweighs_a_handful_of_off_domain_keywords(make_document):
    # Venue is weighted 2x keywords (see domain.py's _VENUE_WEIGHT) — a
    # medical venue should win even when the text itself reads CS-ish.
    doc = make_document(
        venue="The Lancet",
        abstract="We used an algorithm and a neural network to model patient treatment.",
    )
    result = classifier.classify(doc)
    assert result.primary_domain == "medical"


def test_no_signal_falls_back_to_other(make_document):
    doc = make_document(abstract="Nothing relevant to any known domain here.")
    result = classifier.classify(doc)
    assert result.primary_domain == "other"
    assert result.domains == [("other", 0.0)]
    assert result.reasoning


def test_multiple_domains_returned_ranked_by_confidence(make_document):
    doc = make_document(
        abstract=(
            "This paper discusses patient clinical treatment and hospital care, "
            "while also touching on genome and protein structure in cell biology."
        ),
    )
    result = classifier.classify(doc)
    labels = [label for label, _ in result.domains]
    assert "medical" in labels
    assert "biology" in labels
    # Ranked descending.
    assert result.domains == sorted(result.domains, key=lambda pair: pair[1], reverse=True)


def test_matched_features_records_evidence(make_document):
    doc = make_document(abstract="The patient received clinical treatment.")
    result = classifier.classify(doc)
    assert "medical" in result.matched_features
    assert set(result.matched_features["medical"]) >= {"patient", "clinical", "treatment"}


def test_reasoning_is_populated_for_a_real_match(make_document):
    doc = make_document(abstract="The patient received clinical treatment.")
    result = classifier.classify(doc)
    assert result.reasoning
    assert all(isinstance(r, str) and r for r in result.reasoning)
