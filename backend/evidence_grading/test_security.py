import time

import pytest

from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.exceptions import GradingTimeoutError, SecurityError
from backend.evidence_grading.security import PluginIsolator, ResourceGuard, Sanitizer, sanitize_text


def test_resource_guard_check_limits():
    config = EvidenceGradingConfig(max_outcomes=5, max_bias_domains=5, max_rationale_strings=5, max_evidence_references=5)
    guard = ResourceGuard(config)
    assert guard.check_limits(outcome_count=5) is True
    assert guard.check_limits(outcome_count=6) is False


def test_resource_guard_clamps_lists():
    config = EvidenceGradingConfig(max_evidence_references=2, max_rationale_strings=1)
    guard = ResourceGuard(config)
    assert guard.clamp_evidence([1, 2, 3, 4]) == [1, 2]
    assert guard.clamp_rationale(["a", "b"]) == ["a"]


def test_sanitize_text_strips_control_chars_only():
    dirty = "hello\x00world"
    clean = sanitize_text(dirty)
    assert "\x00" not in clean
    assert clean == "helloworld"


def test_sanitizer_sanitize_rationale_clamps_length():
    sanitizer = Sanitizer(max_rationale_length=10)
    result = sanitizer.sanitize_rationale("x" * 50)
    assert len(result) <= 10


def test_plugin_isolator_unrestricted_by_default():
    config = EvidenceGradingConfig()
    isolator = PluginIsolator(config)
    assert isolator.execute_plugin("anything", lambda: 42) == 42


def test_plugin_isolator_rejects_names_outside_allowlist():
    config = EvidenceGradingConfig(plugin_allowlist=["allowed_only"])
    isolator = PluginIsolator(config)
    with pytest.raises(SecurityError):
        isolator.execute_plugin("not_allowed", lambda: 42)
    assert isolator.execute_plugin("allowed_only", lambda: 1) == 1


def test_plugin_isolator_enforces_timeout():
    config = EvidenceGradingConfig(plugin_timeout_ms=50)
    isolator = PluginIsolator(config)

    def _slow():
        time.sleep(2)
        return 1

    with pytest.raises(GradingTimeoutError):
        isolator.execute_plugin("slow", _slow)
