"""Evidence Ranking stage (Phase 2.3 Sprint 2).

Reorders EvidenceObjects from Retrieval. Never invents or mutates objects.
Interprets EvidenceQuery.ranking_strategy (named, versioned).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

RANKING_VERSION = "1.0.0"
SUPPORTED_STRATEGIES = frozenset({"default_v0"})

# Higher is stronger / preferred
_STATUS_SCORE = {
    "accepted": 4,
    "candidate": 3,
    "rejected": 1,
    "superseded": 0,
}
_BAND_SCORE = {"high": 3, "moderate": 2, "low": 1}

_QUALITY_HIGH = frozenset({"high", "a", "1", "1a", "1b"})
_QUALITY_MOD = frozenset({"moderate", "medium", "b", "2", "2a", "2b"})
_QUALITY_LOW = frozenset({"low", "very low", "c", "d", "3", "4", "5"})

_HIGH_DESIGN_TOKENS = (
    "rct",
    "randomized",
    "systematic review",
    "meta-analysis",
    "meta analysis",
)
_MID_DESIGN_TOKENS = ("cohort", "case-control", "case control", "observational", "cross-sectional")
_LOW_DESIGN_TOKENS = ("case report", "case series", "editorial", "opinion", "letter")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _quality_score(study_quality: Any) -> int:
    q = _norm(study_quality)
    if q in _QUALITY_HIGH:
        return 3
    if q in _QUALITY_MOD:
        return 2
    if q in _QUALITY_LOW or q == "":
        return 0 if q == "" else 1
    return 1


def _design_score(study_type: Any) -> int:
    study = _norm(study_type)
    if any(t in study for t in _HIGH_DESIGN_TOKENS):
        return 3
    if any(t in study for t in _MID_DESIGN_TOKENS):
        return 2
    if any(t in study for t in _LOW_DESIGN_TOKENS):
        return 0
    return 1


def _contradiction_score(obj: dict[str, Any]) -> int:
    """Prefer objects without contradict signals (stronger support surface)."""
    contradicts = obj.get("contradicts") or []
    if isinstance(contradicts, list) and len(contradicts) > 0:
        return 0
    return 1


def _recency_ts(obj: dict[str, Any]) -> float:
    """Best-effort recency from DTO / provenance; missing → 0."""
    for key in ("updated_at", "created_at"):
        raw = obj.get(key)
        if raw is None:
            continue
        if isinstance(raw, datetime):
            dt = raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str) and raw.strip():
            try:
                # ISO-ish
                text = raw.replace("Z", "+00:00")
                return datetime.fromisoformat(text).timestamp()
            except ValueError:
                continue
    prov = obj.get("provenance") or {}
    if isinstance(prov, dict):
        for key in ("updated_at", "extracted_at", "created_at"):
            raw = prov.get(key)
            if isinstance(raw, (int, float)):
                return float(raw)
    return 0.0


def default_v0_rank_key(obj: dict[str, Any]) -> tuple:
    """Sort key for default_v0 — strongest first when sorted reverse=True.

    Factors (ADD-0005 Month 3 / Sprint 2):
    Acceptance → confidence band → study quality → study design →
    contradiction-free → recency → stable id.
    """
    status = _norm(obj.get("status"))
    band = _norm(obj.get("confidence_band"))
    return (
        _STATUS_SCORE.get(status, 0),
        _BAND_SCORE.get(band, 0),
        _quality_score(obj.get("study_quality")),
        _design_score(obj.get("study_type")),
        _contradiction_score(obj),
        _recency_ts(obj),
        int(obj.get("id") or 0),
    )


def rank_evidence_objects(
    objects: list[dict[str, Any]],
    *,
    ranking_strategy: str = "default_v0",
) -> list[dict[str, Any]]:
    """Reorder EvidenceObject DTOs. Does not invent or mutate field values."""
    strategy = (ranking_strategy or "default_v0").strip() or "default_v0"
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(f"unsupported ranking_strategy: {strategy}")

    # Stable copy of order only — same object dict identities / contents
    ranked = list(objects)
    if strategy == "default_v0":
        ranked.sort(key=default_v0_rank_key, reverse=True)
    return ranked


def apply_ranking_stage(
    retrieval_result: dict[str, Any],
    *,
    ranking_strategy: str | None = None,
) -> dict[str, Any]:
    """Compose Ranking on a Retrieval-stage envelope. Same object ids, new order."""
    query = retrieval_result.get("query") or {}
    strategy = ranking_strategy or query.get("ranking_strategy") or "default_v0"
    objects = list(retrieval_result.get("objects") or [])
    ranked = rank_evidence_objects(objects, ranking_strategy=strategy)
    return {
        "query": query,
        "objects": ranked,
        "total": retrieval_result.get("total", len(ranked)),
        "truncated": bool(retrieval_result.get("truncated")),
        "stage": "ranking",
        "ranking_version": RANKING_VERSION,
        "ranking_strategy": strategy,
        "retrieval_version": retrieval_result.get("retrieval_version"),
    }
