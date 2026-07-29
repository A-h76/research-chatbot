"""Writing-stage metrics (evaluation-as-process)."""

from __future__ import annotations

from typing import Any


def compute_writing_metrics(
    *,
    sections: list[dict[str, Any]],
    supporting_count: int,
    citations: list[dict[str, Any]],
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Lightweight grounding metrics for every writing response."""
    total = len(sections) or 0
    linked = sum(
        1
        for s in sections
        if s.get("status") == "ok"
        and (s.get("evidence_ids") or s.get("bindings"))
        and not (s.get("orphan_ids") or [])
    )
    empty = sum(1 for s in sections if s.get("status") == "empty")

    cited_ids = {int(c["evidence_id"]) for c in citations if c.get("evidence_id") is not None}
    for s in sections:
        for b in s.get("bindings") or []:
            if b.get("evidence_id") is not None:
                cited_ids.add(int(b["evidence_id"]))

    coverage = (
        round(len(cited_ids) / supporting_count, 4) if supporting_count > 0 else 0.0
    )
    grounding = round(linked / total, 4) if total > 0 else 0.0

    review_metrics = (review or {}).get("metrics") or {}
    if "unsupported_claims" in review_metrics and total > 0:
        unsupported = round(
            min(1.0, float(review_metrics["unsupported_claims"]) / max(total, 1)), 4
        )
    else:
        unsupported = round(empty / total, 4) if total > 0 else 1.0

    if review_metrics.get("grounding_pct") is not None:
        grounding = float(review_metrics["grounding_pct"])
    if review_metrics.get("citation_coverage_pct") is not None:
        coverage = float(review_metrics["citation_coverage_pct"])

    reviewer_pass_rate = float((review or {}).get("pass_rate") or 0.0)

    return {
        "metrics_version": "1.2.0",
        "paragraph_count": total,
        "evidence_linked_paragraphs": linked,
        "grounding_pct": grounding,
        "citation_coverage": coverage,
        "unsupported_sentence_rate": unsupported,
        "unsupported_claims": int(review_metrics.get("unsupported_claims") or 0),
        "unique_evidence_cited": len(cited_ids),
        "supporting_count": supporting_count,
        "reviewer_pass_rate": reviewer_pass_rate,
        "reviewer_status": (review or {}).get("status"),
    }
