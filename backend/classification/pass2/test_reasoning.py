from backend.classification.pass1.rules import SignalMatch
from backend.classification.pass2.enums import ScientificDomain
from backend.classification.pass2.reasoning import build_decision


def test_build_decision_collects_evidence_from_matching_sources_only():
    matching_source = {
        ScientificDomain.MEDICINE: SignalMatch(ScientificDomain.MEDICINE, 0.5, ["patient"], "venue matched medicine")
    }
    non_matching_source = {
        ScientificDomain.BIOLOGY: SignalMatch(ScientificDomain.BIOLOGY, 0.5, ["gene"], "keyword matched biology")
    }

    decision = build_decision(
        ScientificDomain.MEDICINE, 0.6, [matching_source, non_matching_source], ScientificDomain.UNKNOWN
    )

    assert decision.label == ScientificDomain.MEDICINE
    assert decision.confidence == 0.6
    assert decision.evidence == ["venue matched medicine"]
    assert "medicine" in decision.reasoning
    assert "0.60" in decision.reasoning


def test_build_decision_unknown_label_gets_no_reasoning_when_nothing_matched_at_all():
    decision = build_decision(ScientificDomain.UNKNOWN, 0.0, [{}], ScientificDomain.UNKNOWN)
    assert decision.evidence == []
    assert decision.reasoning is None


def test_build_decision_unknown_label_summarizes_a_near_miss():
    # evidence is always empty for the UNKNOWN label itself (nothing is
    # ever keyed by UNKNOWN in a keyword/venue map) — the near-miss
    # summary comes from confidence.resolve()'s preserved sub-threshold
    # score, not from evidence, so this must still produce a reasoning
    # string even though evidence is empty.
    weak_source = {
        ScientificDomain.MEDICINE: SignalMatch(ScientificDomain.MEDICINE, 0.1, ["patient"], "weak keyword hit")
    }
    decision = build_decision(ScientificDomain.UNKNOWN, 0.1, [weak_source], ScientificDomain.UNKNOWN)
    assert decision.evidence == []
    assert decision.reasoning is not None
    assert "0.10" in decision.reasoning
