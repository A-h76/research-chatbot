from backend.classification.pass2.domain import DomainDetector
from backend.classification.pass2.enums import ScientificDomain


def test_detects_medicine_from_venue_alone(document_factory):
    document = document_factory(venue="Published in The Lancet", full_text="nothing domain-specific here")
    decision = DomainDetector().detect(document)
    assert decision.label == ScientificDomain.MEDICINE
    assert decision.confidence >= 0.3


def test_detects_medicine_from_keywords_alone_with_no_venue(document_factory):
    document = document_factory(
        full_text=(
            "The patient was admitted to hospital with a clinical diagnosis requiring treatment and therapy "
            "from a physician in the dental surgical unit of the medicine department."
        )
    )
    decision = DomainDetector().detect(document)
    assert decision.label == ScientificDomain.MEDICINE
    assert decision.confidence >= 0.3


def test_detects_computer_science_from_keywords(document_factory):
    document = document_factory(
        full_text=(
            "We propose a new algorithm for distributed systems using a novel data structure and database "
            "design. Computer science and programming techniques were applied to the operating system."
        )
    )
    decision = DomainDetector().detect(document)
    assert decision.label == ScientificDomain.COMPUTER_SCIENCE


def test_venue_and_keyword_signals_combine(document_factory):
    document = document_factory(
        journal="Physical Review",
        full_text="This paper studies quantum thermodynamics and relativity in astrophysics.",
    )
    decision = DomainDetector().detect(document)
    assert decision.label == ScientificDomain.PHYSICS
    assert decision.confidence > 0.3


def test_no_signal_falls_back_to_unknown(document_factory):
    document = document_factory(full_text="A short generic sentence.")
    decision = DomainDetector().detect(document)
    assert decision.label == ScientificDomain.UNKNOWN
