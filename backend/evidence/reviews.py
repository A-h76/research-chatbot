"""Human review transitions for EvidenceObjects (claim_reviews)."""

from __future__ import annotations

from typing import Any

REVIEW_STATUSES = frozenset({"accepted", "rejected", "edited"})


def validate_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    status = (payload.get("status") or "").strip()
    if status not in REVIEW_STATUSES:
        raise ValueError("status must be accepted|rejected|edited")
    edited_claim = payload.get("edited_claim")
    edited_quote = payload.get("edited_quote")
    if status == "edited" and not (edited_claim or edited_quote):
        raise ValueError("edited reviews require edited_claim or edited_quote")
    return {
        "status": status,
        "reason": (payload.get("reason") or "")[:2000],
        "edited_claim": edited_claim,
        "edited_quote": edited_quote,
    }


def next_object_status_after_review(review_status: str) -> str:
    if review_status == "accepted":
        return "accepted"
    if review_status == "rejected":
        return "rejected"
    # edited → prefer superseding new candidate/accepted via service layer;
    # transitional marker remains accepted when edit applied in place is forbidden.
    return "accepted"
