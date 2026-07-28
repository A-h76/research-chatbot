"""Scoring v0 — ordinal confidence bands from Phase 1.5 + study-type heuristics.

No parallel GRADE stack. API exposes low|moderate|high only.
"""

from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def confidence_band_from_grades(
    *,
    study_type: str | None = None,
    study_quality: str | None = None,
    risk_of_bias: str | None = None,
    consistency: str | None = None,
    has_contradiction: bool = False,
) -> str:
    """Compose an ordinal confidence band.

    Missing grades default conservatively (never invent `high`).
    """
    quality = _norm(study_quality)
    study = _norm(study_type)
    rob = _norm(risk_of_bias)
    cons = _norm(consistency)

    high_design = any(
        token in study
        for token in ("rct", "randomized", "systematic review", "meta-analysis", "meta analysis")
    )
    low_design = any(token in study for token in ("case report", "case series", "editorial", "opinion"))

    quality_high = quality in {"high", "a", "1", "1a", "1b"}
    quality_low = quality in {"low", "very low", "c", "d", "4", "5"} or quality == ""
    rob_high = rob in {"high", "serious", "critical"}
    cons_low = cons in {"low", "inconsistent", "poor"}

    if has_contradiction or rob_high or cons_low or low_design:
        return "low"
    if high_design and quality_high and not quality_low:
        return "high"
    if quality_low and not high_design:
        return "low"
    return "moderate"
