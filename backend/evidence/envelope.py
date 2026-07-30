"""Shared Research Intelligence (RI) response envelope helpers.

All RI stage routes return the same base shape so Frontend / telemetry can
depend on one contract:

    {
      "query": {...},
      "objects": [...],
      "total": N,
      "truncated": false,
      "stage": "retrieval|ranking|consensus|conflict|reasoning|writing",
      "timing_ms": 12,
      "versions": {"retrieval": "1.0.0", ...},
      # plus stage-specific payload / legacy *_version fields
    }

Existing stage-specific keys (`retrieval_version`, `consensus`, …) stay
additive for backward compatibility.
"""

from __future__ import annotations

from typing import Any

VERSION_FIELD_BY_STAGE = (
    ("retrieval", "retrieval_version"),
    ("ranking", "ranking_version"),
    ("consensus", "consensus_version"),
    ("conflict", "conflict_version"),
    ("reasoning", "reasoning_version"),
    ("writing", "writing_version"),
)


def collect_versions(result: dict[str, Any]) -> dict[str, str]:
    """Normalize scattered `*_version` fields into a single `versions` map."""
    versions: dict[str, str] = {}
    for stage_name, field in VERSION_FIELD_BY_STAGE:
        value = result.get(field)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            versions[stage_name] = text
    return versions


def stamp_ri_envelope(
    result: dict[str, Any],
    *,
    timing_ms: int | float | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    """Return a copy of `result` with the shared RI envelope fields filled in."""
    out = dict(result)
    if stage is not None:
        out["stage"] = stage

    if "stage" not in out or not str(out["stage"]).strip():
        raise ValueError("RI envelope requires stage")

    out.setdefault("query", {})
    objects = out.get("objects")
    if not isinstance(objects, list):
        objects = []
        out["objects"] = objects
    out.setdefault("total", len(objects))
    out.setdefault("truncated", False)

    out["versions"] = collect_versions(out)

    if timing_ms is not None:
        out["timing_ms"] = max(0, int(round(float(timing_ms))))

    return out
