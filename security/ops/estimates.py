"""Pre-flight cost estimates (foundation for pricing plans)."""

from __future__ import annotations


def estimate_chat_tokens(message: str, *, history_chars: int = 0) -> int:
    """Rough token estimate for a pre-request quota check."""
    chars = len(message or "") + max(0, history_chars)
    return max(200, chars // 4 + 500)


def estimate_research_cost_usd(
    cost_ledger,
    *,
    model: str,
    papers_json_chars: int,
    completion_tokens: int = 2500,
) -> dict:
    """Estimate research call cost from packed papers size.

    Returns estimated_cost (USD), estimated_prompt_tokens, estimated_completion_tokens.
    """
    prompt_tokens = max(800, papers_json_chars // 4 + 1200)
    cost = cost_ledger.estimate_cost(model, prompt_tokens, completion_tokens)
    return {
        "estimated_cost": cost,
        "estimated_cost_usd": cost,
        "currency": "USD",
        "estimated_prompt_tokens": prompt_tokens,
        "estimated_completion_tokens": completion_tokens,
        "model": model,
    }
