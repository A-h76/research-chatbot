"""Research Decisions — persistent project memory (Phase A.2).

User-facing labels (never expose backend type names in product UI):
  ACCEPT → Accepted
  REJECT → Rejected
  IMPORTANT → Important
  OPEN_QUESTION → Needs Review
  SUPPORT → Supports
  CONTRADICT → Contradiction

Decisions accumulate quietly; no Decision Dashboard / Analytics / Graph yet.
"""

from __future__ import annotations

from typing import Any

DECISION_TYPES = frozenset(
    {
        "ACCEPT",
        "REJECT",
        "IMPORTANT",
        "OPEN_QUESTION",
        "SUPPORT",
        "CONTRADICT",
    }
)

# Product labels shown to researchers
DECISION_LABELS: dict[str, str] = {
    "ACCEPT": "Accepted",
    "REJECT": "Rejected",
    "IMPORTANT": "Important",
    "OPEN_QUESTION": "Needs Review",
    "SUPPORT": "Supports",
    "CONTRADICT": "Contradiction",
}

# Optional "Why?" presets — free text still allowed via reason
REASON_PRESETS: dict[str, tuple[str, ...]] = {
    "ACCEPT": (
        "High quality methodology",
        "Supports hypothesis",
        "Key finding",
        "Use in discussion",
        "Use in introduction",
        "Other",
    ),
    "REJECT": (
        "Not relevant",
        "Weak methodology",
        "Small sample / low quality",
        "Duplicate claim",
        "Other",
    ),
    "IMPORTANT": (
        "Future work",
        "Key finding",
        "Use in discussion",
        "Other",
    ),
    "OPEN_QUESTION": (
        "Needs explanation",
        "Unresolved conflict",
        "Follow up later",
        "Other",
    ),
    "SUPPORT": (
        "Supports hypothesis",
        "Supports claim",
        "Other",
    ),
    "CONTRADICT": (
        "Methodological difference",
        "Conflicting finding",
        "Needs explanation",
        "Other",
    ),
}

# Map ClaimReview statuses → decision types
REVIEW_STATUS_TO_DECISION = {
    "accepted": "ACCEPT",
    "rejected": "REJECT",
    "edited": "ACCEPT",
}


def validate_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw = (payload.get("type") or payload.get("decision_type") or "").strip().upper()
    if raw not in DECISION_TYPES:
        raise ValueError(
            "type must be ACCEPT|REJECT|IMPORTANT|OPEN_QUESTION|SUPPORT|CONTRADICT"
        )
    evidence_id = payload.get("evidence_id") or payload.get("evidence_object_id")
    if evidence_id is None:
        raise ValueError("evidence_id is required")
    try:
        eid = int(evidence_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("evidence_id must be an integer") from exc
    if eid <= 0:
        raise ValueError("evidence_id must be positive")

    reason = (payload.get("reason") or "").strip()[:2000]
    reason_code = (payload.get("reason_code") or "").strip()[:120]
    if reason_code and not reason:
        # Prefer human-readable preset text when only code/label sent
        reason = reason_code

    return {
        "type": raw,
        "evidence_id": eid,
        "reason": reason,
        "reason_code": reason_code[:120] if reason_code else "",
    }


def serialize_decision(
    row: Any,
    *,
    claim_preview: str = "",
) -> dict[str, Any]:
    dtype = str(getattr(row, "decision_type", "") or "")
    return {
        "id": getattr(row, "id", None),
        "project_id": getattr(row, "project_id", None),
        "evidence_id": getattr(row, "evidence_object_id", None),
        "type": dtype,
        "label": DECISION_LABELS.get(dtype, dtype),
        "reason": getattr(row, "reason", "") or "",
        "reason_code": getattr(row, "reason_code", "") or "",
        "user_id": getattr(row, "user_id", None),
        "timestamp": (
            getattr(row, "created_at", None).isoformat()
            if getattr(row, "created_at", None) is not None
            else None
        ),
        "claim_preview": (claim_preview or "")[:240],
    }


def decision_type_from_review_status(status: str) -> str:
    return REVIEW_STATUS_TO_DECISION.get((status or "").strip().lower(), "ACCEPT")
