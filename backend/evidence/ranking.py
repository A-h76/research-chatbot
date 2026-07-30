"""Evidence Ranking stage (Phase 2.3 Sprint 2 + A-403 strategies).

Reorders EvidenceObjects from Retrieval. Never invents or mutates objects.
Interprets EvidenceQuery.ranking_strategy (named, versioned registry).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

RANKING_VERSION = "1.1.0"

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


def factor_scores(obj: dict[str, Any]) -> dict[str, float | int]:
    """Explainable factor breakdown (does not mutate obj)."""
    status = _norm(obj.get("status"))
    band = _norm(obj.get("confidence_band"))
    return {
        "status": _STATUS_SCORE.get(status, 0),
        "confidence_band": _BAND_SCORE.get(band, 0),
        "study_quality": _quality_score(obj.get("study_quality")),
        "study_design": _design_score(obj.get("study_type")),
        "contradiction_free": _contradiction_score(obj),
        "recency_ts": _recency_ts(obj),
        "id": int(obj.get("id") or 0),
    }


def default_v0_rank_key(obj: dict[str, Any]) -> tuple:
    """Sort key for default_v0 — strongest first when sorted reverse=True.

    Factors:
    Acceptance → confidence band → study quality → study design →
    contradiction-free → recency → stable id.
    """
    f = factor_scores(obj)
    return (
        f["status"],
        f["confidence_band"],
        f["study_quality"],
        f["study_design"],
        f["contradiction_free"],
        f["recency_ts"],
        f["id"],
    )


def quality_first_v1_rank_key(obj: dict[str, Any]) -> tuple:
    """Quality → design → band → status → contradiction-free → recency → id."""
    f = factor_scores(obj)
    return (
        f["study_quality"],
        f["study_design"],
        f["confidence_band"],
        f["status"],
        f["contradiction_free"],
        f["recency_ts"],
        f["id"],
    )


def recency_v1_rank_key(obj: dict[str, Any]) -> tuple:
    """Prefer accepted, then newest, then band/quality (library freshness)."""
    f = factor_scores(obj)
    return (
        f["status"],
        f["recency_ts"],
        f["confidence_band"],
        f["study_quality"],
        f["study_design"],
        f["contradiction_free"],
        f["id"],
    )


def confidence_weighted_v1_score(obj: dict[str, Any]) -> float:
    """Composite numeric score emphasizing confidence band (A-403).

    Still respects acceptance status as the dominant term so rejected
    objects cannot outrank accepted ones via a high band alone.
    """
    f = factor_scores(obj)
    # recency contributes a small fractional boost (seconds → [0, ~1] over decades)
    recency_boost = min(float(f["recency_ts"]) / 1.0e10, 1.0) if f["recency_ts"] else 0.0
    return (
        float(f["status"]) * 1000.0
        + float(f["confidence_band"]) * 80.0
        + float(f["study_quality"]) * 25.0
        + float(f["study_design"]) * 15.0
        + float(f["contradiction_free"]) * 10.0
        + recency_boost
    )


def confidence_weighted_v1_rank_key(obj: dict[str, Any]) -> tuple:
    return (confidence_weighted_v1_score(obj), int(obj.get("id") or 0))


STRATEGY_REGISTRY: dict[str, dict[str, Any]] = {
    "default_v0": {
        "version": "1.0.0",
        "description": "Acceptance → band → quality → design → contradiction-free → recency",
        "rank_key": default_v0_rank_key,
    },
    "quality_first_v1": {
        "version": "1.1.0",
        "description": "Study quality → design → band → status → contradiction-free → recency",
        "rank_key": quality_first_v1_rank_key,
    },
    "recency_v1": {
        "version": "1.1.0",
        "description": "Status → recency → band → quality (freshest accepted first)",
        "rank_key": recency_v1_rank_key,
    },
    "confidence_weighted_v1": {
        "version": "1.1.0",
        "description": "Composite score weighted toward confidence_band (explainable diagnostics)",
        "rank_key": confidence_weighted_v1_rank_key,
    },
}

SUPPORTED_STRATEGIES = frozenset(STRATEGY_REGISTRY.keys())


def list_ranking_strategies() -> list[dict[str, str]]:
    """Public registry snapshot for docs / future discovery endpoint."""
    return [
        {
            "name": name,
            "version": str(meta["version"]),
            "description": str(meta["description"]),
        }
        for name, meta in STRATEGY_REGISTRY.items()
    ]


def build_ranking_diagnostics(
    objects: list[dict[str, Any]],
    *,
    ranking_strategy: str,
) -> dict[str, Any]:
    """Side-channel scores — never written onto EvidenceObject DTOs."""
    object_scores: dict[str, dict[str, Any]] = {}
    for obj in objects:
        oid = obj.get("id")
        if oid is None:
            continue
        factors = factor_scores(obj)
        entry: dict[str, Any] = {"factors": factors}
        if ranking_strategy == "confidence_weighted_v1":
            entry["composite"] = round(confidence_weighted_v1_score(obj), 4)
        object_scores[str(int(oid))] = entry
    return {
        "strategy": ranking_strategy,
        "ranking_version": RANKING_VERSION,
        "object_scores": object_scores,
    }


def rank_evidence_objects(
    objects: list[dict[str, Any]],
    *,
    ranking_strategy: str = "default_v0",
) -> list[dict[str, Any]]:
    """Reorder EvidenceObject DTOs. Does not invent or mutate field values."""
    strategy = (ranking_strategy or "default_v0").strip() or "default_v0"
    meta = STRATEGY_REGISTRY.get(strategy)
    if meta is None:
        raise ValueError(f"unsupported ranking_strategy: {strategy}")

    ranked = list(objects)
    key_fn: Callable[[dict[str, Any]], Any] = meta["rank_key"]
    ranked.sort(key=key_fn, reverse=True)
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
        "ranking_diagnostics": build_ranking_diagnostics(ranked, ranking_strategy=strategy),
        "retrieval_version": retrieval_result.get("retrieval_version"),
    }
