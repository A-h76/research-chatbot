"""Plan policy table — Free / Pro / Team / Enterprise (+ beta/student).

Limits are data, not scattered if/else in routes. Plans unknown to the
table fall back to ``beta`` (closed-beta default).
"""

from __future__ import annotations

from typing import Any

# Soft-warn when used/limit >= WARN_RATIO; hard block at 100%.
WARN_RATIO = 0.80

PLAN_LIMITS: dict[str, dict[str, Any]] = {
    "free": {
        "monthly_token_limit": 100_000,
        "monthly_cost_limit": 3.0,
        "max_projects": 5,
        "max_research_day": 5,
        "max_active_research": 3,
        "storage_limit_bytes": 1_000_000_000,
    },
    "beta": {
        "monthly_token_limit": 1_000_000,
        "monthly_cost_limit": 20.0,
        "max_projects": 50,
        "max_research_day": 50,
        "max_active_research": 5,
        "storage_limit_bytes": 5_000_000_000,
    },
    "student": {
        "monthly_token_limit": 10_000_000,
        "monthly_cost_limit": 20.0,
        "max_projects": 100,
        "max_research_day": 50,
        "max_active_research": 5,
        "storage_limit_bytes": 10_000_000_000,
    },
    "pro": {
        "monthly_token_limit": 50_000_000,
        "monthly_cost_limit": 100.0,
        "max_projects": 500,
        "max_research_day": 200,
        "max_active_research": 8,
        "storage_limit_bytes": 50_000_000_000,
    },
    "team": {
        "monthly_token_limit": 200_000_000,
        "monthly_cost_limit": 400.0,
        "max_projects": 2_000,
        "max_research_day": 500,
        "max_active_research": 20,
        "storage_limit_bytes": 200_000_000_000,
    },
    "enterprise": {
        "monthly_token_limit": 1_000_000_000,
        "monthly_cost_limit": 0.0,  # 0 = custom / unlimited cost (token cap still applies unless overridden)
        "max_projects": 50_000,
        "max_research_day": 5_000,
        "max_active_research": 100,
        "storage_limit_bytes": 2_000_000_000_000,
    },
}


def plan_limits(plan: str | None) -> dict[str, Any]:
    key = (plan or "beta").strip().lower()
    return dict(PLAN_LIMITS.get(key, PLAN_LIMITS["beta"]))
