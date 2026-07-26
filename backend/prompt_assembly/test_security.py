"""Security tests for sanitizers and token limits."""

from backend.prompt_assembly.config import PromptAssemblyConfig
from backend.prompt_assembly.security.limits import TokenLimiter
from backend.prompt_assembly.security.sanitizers import ContentSanitizer, safe_fill_template, strip_html


def test_strip_html():
    assert "<" not in strip_html("<script>alert(1)</script>hello")


def test_safe_fill_only_allowed_keys():
    out = safe_fill_template(
        "{title} {abstract} {hacked}",
        {"title": "T", "abstract": "A", "hacked": "BAD"},
        allowed_keys={"title", "abstract"},
    )
    assert out == "T A "
    assert "BAD" not in out


def test_token_limiter_truncates():
    config = PromptAssemblyConfig(max_total_prompt_tokens=5, token_estimation_strategy="word_count")  # type: ignore[arg-type]
    from backend.prompt_assembly.enums import TokenEstimationStrategy

    config.token_estimation_strategy = TokenEstimationStrategy.WORD_COUNT
    config.max_total_prompt_tokens = 2
    limiter = TokenLimiter(config)
    text = "alpha beta gamma delta epsilon zeta"
    truncated, was = limiter.check_and_truncate(text)
    assert was is True
    assert len(truncated) < len(text)


def test_sanitizer_strips_control_and_html():
    cleaned = ContentSanitizer(max_length=50).sanitize("hi\x00<script>x</script>there")
    assert "\x00" not in cleaned
    assert "<script>" not in cleaned
