"""Metered operations — every expensive workflow maps to one entitlement key."""

from __future__ import annotations

from typing import Any

# operation_id → display + default unit estimate (tokens) + cost hint (USD)
OPERATIONS: dict[str, dict[str, Any]] = {
    "chat": {
        "label": "Chat",
        "category": "ai",
        "default_tokens": 800,
        "default_cost_usd": 0.01,
        "unit": "tokens",
    },
    "writing_intelligence": {
        "label": "Writing Intelligence",
        "category": "ai",
        "default_tokens": 8_000,
        "default_cost_usd": 0.08,
        "unit": "tokens",
    },
    "research_reviewer": {
        "label": "Research Reviewer",
        "category": "ai",
        "default_tokens": 4_000,
        "default_cost_usd": 0.04,
        "unit": "tokens",
    },
    "evidence_extract": {
        "label": "Evidence extraction",
        "category": "ai",
        "default_tokens": 6_000,
        "default_cost_usd": 0.06,
        "unit": "tokens",
    },
    "paper_upload": {
        "label": "Paper upload",
        "category": "storage",
        "default_tokens": 0,
        "default_cost_usd": 0.0,
        "unit": "bytes",
    },
    "pdf_import": {
        "label": "PDF import",
        "category": "storage",
        "default_tokens": 0,
        "default_cost_usd": 0.0,
        "unit": "bytes",
    },
    "library_sync": {
        "label": "Library sync",
        "category": "ai",
        "default_tokens": 200,
        "default_cost_usd": 0.0,
        "unit": "tokens",
    },
    "discover_search": {
        "label": "Discovery search",
        "category": "ai",
        "default_tokens": 400,
        "default_cost_usd": 0.002,
        "unit": "tokens",
    },
    "embeddings": {
        "label": "Embeddings",
        "category": "ai",
        "default_tokens": 1_000,
        "default_cost_usd": 0.005,
        "unit": "tokens",
    },
    "export": {
        "label": "Export generation",
        "category": "ai",
        "default_tokens": 500,
        "default_cost_usd": 0.0,
        "unit": "tokens",
    },
    "project_research": {
        "label": "Project research",
        "category": "ai",
        "default_tokens": 10_000,
        "default_cost_usd": 0.10,
        "unit": "tokens",
    },
    "agent_run": {
        "label": "Agent run",
        "category": "ai",
        "default_tokens": 12_000,
        "default_cost_usd": 0.12,
        "unit": "tokens",
    },
}


def get_operation(operation: str) -> dict[str, Any]:
    key = (operation or "").strip().lower()
    if key not in OPERATIONS:
        return {
            "label": key or "Operation",
            "category": "ai",
            "default_tokens": 500,
            "default_cost_usd": 0.01,
            "unit": "tokens",
        }
    return dict(OPERATIONS[key])
