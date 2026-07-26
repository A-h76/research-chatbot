from backend.medical_understanding.config import MedicalUnderstandingConfig
from backend.medical_understanding.security.sanitizers import clamp_context, sanitize_paragraph, sanitize_text


def test_strips_control_characters():
    assert sanitize_text("hello\x00world\x01") == "helloworld"


def test_truncates_to_max_length():
    assert sanitize_text("abcdefgh", max_length=4) == "abcd"


def test_empty_and_none_safe():
    assert sanitize_text("") == ""
    assert sanitize_text(None) == ""


def test_sanitize_paragraph_uses_config_limit():
    config = MedicalUnderstandingConfig(max_paragraph_size=5)
    assert sanitize_paragraph("abcdefgh", config) == "abcde"


def test_clamp_context_uses_config_limit():
    config = MedicalUnderstandingConfig(max_context_length=3)
    assert clamp_context("abcdefgh", config) == "abc"
