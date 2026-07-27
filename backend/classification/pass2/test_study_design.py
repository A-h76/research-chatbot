from backend.classification.pass2.enums import StudyDesign
from backend.classification.pass2.study_design import StudyDesignDetector


def test_detects_rct(document_factory):
    document = document_factory(
        full_text=(
            "This randomized controlled trial used a double-blind, placebo-controlled design with "
            "random allocation of participants who were randomly assigned to each arm."
        )
    )
    decision = StudyDesignDetector().detect(document)
    assert decision.label == StudyDesign.RCT


def test_detects_benchmark(document_factory):
    document = document_factory(
        full_text="We benchmark our approach against a strong baseline comparison using a public leaderboard "
        "and a well-known benchmark dataset."
    )
    decision = StudyDesignDetector().detect(document)
    assert decision.label == StudyDesign.BENCHMARK


def test_detects_qualitative_study(document_factory):
    document = document_factory(
        full_text="This qualitative study used thematic analysis and grounded theory based on "
        "semi-structured interviews and focus groups."
    )
    decision = StudyDesignDetector().detect(document)
    assert decision.label == StudyDesign.QUALITATIVE


def test_no_signal_falls_back_to_unknown(document_factory):
    document = document_factory(full_text="A generic sentence with no study design markers.")
    decision = StudyDesignDetector().detect(document)
    assert decision.label == StudyDesign.UNKNOWN
