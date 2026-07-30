"""Evidence Query v0 contract helpers (Phase 2.3 Sprint 0)."""

from __future__ import annotations

from typing import Any

INTENTS = frozenset(
    {
        "support_sentence",
        "answer_question",
        "review_coverage",
        "compare_topic",
        "list_project",
    }
)
# Append-only Writing Intelligence section types (Milestone 1).
SECTION_TYPES = frozenset(
    {
        "support_sentence",
        "introduction",
        "literature_review",
        "discussion",
        "clinical_summary",
        "research_gap",
        "executive_summary",
    }
)
BANDS = frozenset({"low", "moderate", "high"})
STATUSES = frozenset({"candidate", "accepted", "rejected", "superseded"})

# Platform contract forbids these keys on EvidenceQuery
FORBIDDEN_KEYS = frozenset(
    {
        "prompt",
        "model",
        "temperature",
        "embeddings",
        "vector_index",
        "api_key",
        "provider",
    }
)


def normalize_evidence_query(raw: dict[str, Any], *, user_id: int) -> dict[str, Any]:
    """Validate and normalize an EvidenceQuery. Raises ValueError on contract break."""
    if not isinstance(raw, dict):
        raise ValueError("evidence_query must be an object")

    bad = FORBIDDEN_KEYS.intersection(raw.keys())
    if bad:
        raise ValueError(f"evidence_query must not include {sorted(bad)}")

    intent = str(raw.get("intent") or "").strip()
    if intent not in INTENTS:
        raise ValueError(f"invalid intent: {intent}")

    scope_in = raw.get("scope") or {}
    if not isinstance(scope_in, dict):
        raise ValueError("scope must be an object")
    if scope_in.get("project_id") is None:
        raise ValueError("scope.project_id is required")
    # Client-supplied user_id is ignored; server binds authenticated user
    scope = {
        "user_id": int(user_id),
        "project_id": int(scope_in["project_id"]),
        "file_ids": scope_in.get("file_ids"),
        "document_id": scope_in.get("document_id"),
    }
    if scope["file_ids"] is not None:
        if not isinstance(scope["file_ids"], list):
            raise ValueError("scope.file_ids must be a list or null")
        scope["file_ids"] = [int(x) for x in scope["file_ids"]]

    filters_in = raw.get("filters") or {}
    if not isinstance(filters_in, dict):
        raise ValueError("filters must be an object")
    status = list(filters_in.get("status") or ["accepted"])
    bands = list(filters_in.get("confidence_bands") or ["high", "moderate", "low"])
    if any(s not in STATUSES for s in status):
        raise ValueError("invalid filters.status")
    if any(b not in BANDS for b in bands):
        raise ValueError("invalid filters.confidence_bands")

    strategy = str(raw.get("ranking_strategy") or "default_v0").strip() or "default_v0"
    # Validate early so search/retrieve/consensus reject unknown strategies (A-403 / A-602).
    from backend.evidence.ranking import SUPPORTED_STRATEGIES

    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(f"unsupported ranking_strategy: {strategy}")
    try:
        limit = int(raw.get("result_limit", 20))
    except (TypeError, ValueError) as exc:
        raise ValueError("result_limit must be an int") from exc
    limit = max(1, min(100, limit))

    anchors_in = raw.get("anchors") or {}
    if anchors_in is None:
        anchors_in = {}
    if not isinstance(anchors_in, dict):
        raise ValueError("anchors must be an object")

    section_raw = raw.get("section_type")
    if section_raw is None or section_raw == "":
        section_type = "support_sentence"
    else:
        section_type = str(section_raw).strip().lower()
        if section_type not in SECTION_TYPES:
            raise ValueError(f"invalid section_type: {section_type}")

    return {
        "intent": intent,
        "scope": scope,
        "filters": {
            "status": status,
            "confidence_bands": bands,
            "study_types": list(filters_in.get("study_types") or []),
            "require_page_anchor": bool(filters_in.get("require_page_anchor", True)),
        },
        "ranking_strategy": strategy,
        "result_limit": limit,
        "query_text": (raw.get("query_text") or "")[:4000],
        "anchors": {
            "block_id": (anchors_in.get("block_id") or "")[:120],
            "selected_text": (anchors_in.get("selected_text") or "")[:2000],
        },
        "section_type": section_type,
    }
