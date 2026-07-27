from backend.medical_understanding.config import MedicalUnderstandingConfig
from backend.medical_understanding.security.limits import ResourceGuard


def test_within_limits_returns_true():
    guard = ResourceGuard(MedicalUnderstandingConfig(max_entities=100, max_relations=50))
    assert guard.check_limits(entity_count=10, relation_count=5) is True


def test_entity_limit_exceeded_returns_false():
    guard = ResourceGuard(MedicalUnderstandingConfig(max_entities=100))
    assert guard.check_limits(entity_count=101, relation_count=0) is False


def test_relation_limit_exceeded_returns_false():
    guard = ResourceGuard(MedicalUnderstandingConfig(max_relations=50))
    assert guard.check_limits(entity_count=0, relation_count=51) is False


def test_clamp_evidence_truncates_to_max():
    guard = ResourceGuard(MedicalUnderstandingConfig(max_evidence_references=3))
    assert guard.clamp_evidence([1, 2, 3, 4, 5]) == [1, 2, 3]


def test_clamp_evidence_leaves_short_list_untouched():
    guard = ResourceGuard(MedicalUnderstandingConfig(max_evidence_references=10))
    assert guard.clamp_evidence([1, 2]) == [1, 2]
