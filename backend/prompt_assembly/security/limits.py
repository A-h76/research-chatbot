"""Resource and token limits for prompt assembly."""

from ..config import PromptAssemblyConfig
from ..enums import TokenEstimationStrategy


def estimate_tokens(text: str, strategy: TokenEstimationStrategy = TokenEstimationStrategy.WORD_COUNT) -> int:
    """Conservative token estimate — no hard dependency on tiktoken."""
    text = text or ""
    words = max(1, len(text.split())) if text.strip() else 0
    chars = len(text)
    by_words = int(words / 0.75) if words else 0
    by_chars = int(chars / 4) if chars else 0

    if strategy == TokenEstimationStrategy.WORD_COUNT:
        return by_words
    if strategy == TokenEstimationStrategy.CHARACTER_COUNT:
        return by_chars
    if strategy == TokenEstimationStrategy.TIKTOKEN:
        try:
            import tiktoken  # type: ignore

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:  # noqa: BLE001 — optional dep; fall through to hybrid
            return max(by_words, by_chars)
    # HYBRID — take the larger estimate (safer against truncation)
    return max(by_words, by_chars)


class ResourceGuard:
    def __init__(self, config: PromptAssemblyConfig) -> None:
        self.max_prompt_length = config.max_prompt_length
        self.max_section_length = config.max_section_length
        self.max_abstract_length = config.max_abstract_length
        self.max_entities = config.max_entities
        self.max_components = config.max_components
        self.max_evidence_per_claim = config.max_evidence_per_claim

    def clamp_text(self, text: str, max_length: int | None = None) -> str:
        limit = max_length if max_length is not None else self.max_prompt_length
        return (text or "")[:limit]

    def clamp_section(self, text: str) -> str:
        return self.clamp_text(text, self.max_section_length)

    def clamp_abstract(self, text: str) -> str:
        return self.clamp_text(text, self.max_abstract_length)


class TokenLimiter:
    def __init__(self, config: PromptAssemblyConfig) -> None:
        self.max_tokens = config.max_total_prompt_tokens
        self.strategy = config.token_estimation_strategy

    def estimate(self, prompt: str) -> int:
        return estimate_tokens(prompt, self.strategy)

    def check_and_truncate(self, prompt: str) -> tuple[str, bool]:
        """Returns (possibly truncated prompt, was_truncated). Truncation
        is character-based using the char≈4-token heuristic so we never
        need tiktoken for the truncate path."""
        tokens = self.estimate(prompt)
        if tokens <= self.max_tokens:
            return prompt, False
        max_chars = self.max_tokens * 4
        return prompt[:max_chars], True
