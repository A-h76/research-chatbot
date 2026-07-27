from backend.evidence_grading.audit import (
    record_aggregation,
    record_conflict_resolution,
    record_downgrade,
    record_upgrade,
)
from backend.evidence_grading.enums import GradingFramework
from backend.evidence_grading.models import AuditTrail


def test_add_decision_derives_confidence_chain():
    trail = AuditTrail()
    trail.add_decision(
        decision_id="d1", rule="rule1", evidence=[], framework=GradingFramework.GRADE, confidence_delta=-0.2, result="downgraded"
    )
    trail.add_decision(
        decision_id="d2", rule="rule2", evidence=[], framework=GradingFramework.GRADE, confidence_delta=0.1, result="upgraded"
    )
    first, second = trail.decisions
    assert first.confidence_before == 0.0
    assert first.confidence_after == -0.2
    assert second.confidence_before == -0.2
    assert second.confidence_after == -0.1
    assert first.reasoning == "rule1 -> downgraded"


def test_record_downgrade_and_upgrade_deltas():
    trail = AuditTrail()
    record_downgrade(trail, GradingFramework.GRADE, "risk_of_bias", levels=2, evidence=[])
    record_upgrade(trail, GradingFramework.GRADE, "large_effect", levels=1, evidence=[])
    assert trail.decisions[0].confidence_delta == -0.2
    assert trail.decisions[0].result == "downgraded by 2 level(s)"
    assert trail.decisions[1].confidence_delta == 0.1


def test_record_aggregation_and_conflict_resolution():
    trail = AuditTrail()
    record_aggregation(trail, strategy="weighted_average", result="high", evidence=[])
    record_conflict_resolution(trail, resolution_strategy="majority", resolved_value="moderate", evidence=[])
    assert trail.decisions[0].framework == GradingFramework.UNKNOWN
    assert trail.decisions[1].result == "resolved to 'moderate'"
