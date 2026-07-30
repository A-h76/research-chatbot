"""Persist Research Reviewer runs for historical reconstruction (A-401 / A-503).

Distinct from claim_reviews (human EvidenceObject accept/reject).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(raw: str | None, default: Any):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def build_input_snapshot(
    *,
    sections: list[dict[str, Any]] | None,
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
    supporting_count: int | None,
    evidence_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Compact snapshot so later EvidenceObject edits do not rewrite history."""
    section_rows = []
    collected_ids: set[int] = set(evidence_ids or [])
    for sec in sections or []:
        bindings = list(sec.get("bindings") or [])
        eids = []
        for b in bindings:
            if b.get("evidence_id") is not None:
                eid = int(b["evidence_id"])
                eids.append(eid)
                collected_ids.add(eid)
        for raw in sec.get("evidence_ids") or []:
            try:
                collected_ids.add(int(raw))
            except (TypeError, ValueError):
                pass
        section_rows.append(
            {
                "id": sec.get("id"),
                "title": sec.get("title"),
                "status": sec.get("status"),
                "evidence_ids": eids or list(sec.get("evidence_ids") or []),
                "paragraph_hash": _stable_hash(sec.get("paragraph") or ""),
                "paragraph_preview": (sec.get("paragraph") or "")[:240],
            }
        )
    return {
        "sections": section_rows,
        "evidence_ids": sorted(collected_ids),
        "supporting_count": supporting_count,
        "consensus_label": (consensus or {}).get("label"),
        "conflict_has_conflict": bool((conflict or {}).get("has_conflict")),
        "conflict_mediators": list((conflict or {}).get("mediators") or []),
    }


def _stable_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def enrich_issues_with_evidence_ids(
    issues: list[dict[str, Any]],
    sections: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    by_section: dict[str, list[int]] = {}
    for sec in sections or []:
        sid = str(sec.get("id") or "")
        ids: list[int] = []
        for b in sec.get("bindings") or []:
            if b.get("evidence_id") is not None:
                ids.append(int(b["evidence_id"]))
        for raw in sec.get("evidence_ids") or []:
            try:
                ids.append(int(raw))
            except (TypeError, ValueError):
                pass
        by_section[sid] = sorted(set(ids))

    out = []
    for issue in issues or []:
        row = dict(issue)
        if "evidence_ids" not in row or row.get("evidence_ids") is None:
            sid = row.get("section_id")
            row["evidence_ids"] = by_section.get(str(sid or ""), [])
        out.append(row)
    return out


def persist_reviewer_run(
    db,
    *,
    ReviewerRun: Any,
    ReviewerFinding: Any,
    user_id: int,
    project_id: int,
    document_id: int,
    document_version_no: int,
    writing_version: str,
    review: dict[str, Any],
    sections: list[dict[str, Any]] | None = None,
    consensus: dict[str, Any] | None = None,
    conflict: dict[str, Any] | None = None,
    supporting_count: int | None = None,
    model_version_id: int | None = None,
    prompt_version_id: int | None = None,
    prompt_meta: dict[str, Any] | None = None,
    binder_version: str = "",
) -> Any:
    """Write reviewer_runs + reviewer_findings; returns ReviewerRun row (flushed)."""
    now = datetime.now(timezone.utc)
    issues = enrich_issues_with_evidence_ids(list(review.get("issues") or []), sections)
    snapshot = build_input_snapshot(
        sections=sections,
        consensus=consensus,
        conflict=conflict,
        supporting_count=supporting_count,
        evidence_ids=[
            eid
            for issue in issues
            for eid in (issue.get("evidence_ids") or [])
            if eid is not None
        ],
    )
    metrics = dict(review.get("metrics") or {})
    # Confidence-oriented rollup for audit (deterministic from metrics).
    metrics.setdefault("pass_rate", review.get("pass_rate"))
    metrics.setdefault(
        "confidence",
        {
            "grounding_pct": metrics.get("grounding_pct"),
            "citation_coverage_pct": metrics.get("citation_coverage_pct"),
            "pass_rate": review.get("pass_rate"),
            "status": review.get("status"),
        },
    )

    run = ReviewerRun(
        user_id=user_id,
        project_id=project_id,
        document_id=document_id,
        document_version_no=int(document_version_no or 1),
        writing_version=str(writing_version or ""),
        reviewer_version=str(review.get("reviewer_version") or ""),
        binder_version=str(binder_version or ""),
        status=str(review.get("status") or "fail"),
        pass_rate=float(review.get("pass_rate") or 0.0),
        sections_checked=int(review.get("sections_checked") or 0),
        sections_passed=int(review.get("sections_passed") or 0),
        issue_count=int(review.get("issue_count") or len(issues)),
        metrics_json=_json_dumps(metrics),
        input_snapshot_json=_json_dumps(snapshot),
        model_version_id=model_version_id,
        prompt_version_id=prompt_version_id,
        prompt_meta_json=_json_dumps(prompt_meta or {}),
        created_at=now,
        finished_at=now,
    )
    db.add(run)
    db.flush()

    for issue in issues:
        finding = ReviewerFinding(
            run_id=run.id,
            code=str(issue.get("code") or "unknown")[:80],
            severity=str(issue.get("severity") or "warning")[:20],
            message=str(issue.get("message") or ""),
            section_id=(str(issue["section_id"]) if issue.get("section_id") is not None else None),
            block_id=str(issue.get("block_id") or "")[:120],
            range_start=issue.get("range_start"),
            range_end=issue.get("range_end"),
            selected_text=str(issue.get("selected_text") or ""),
            evidence_ids_json=_json_dumps(list(issue.get("evidence_ids") or [])),
            confidence_band=str(issue.get("confidence_band") or "")[:20],
            recommendation=str(issue.get("recommendation") or ""),
            status="open",
            resolution_rationale="",
            resolved_at=None,
            resolved_by=None,
            created_at=now,
        )
        db.add(finding)
    db.flush()
    return run


def serialize_finding(row: Any) -> dict[str, Any]:
    resolved_at = getattr(row, "resolved_at", None)
    created_at = getattr(row, "created_at", None)
    return {
        "id": row.id,
        "run_id": row.run_id,
        "code": row.code,
        "severity": row.severity,
        "message": row.message or "",
        "section_id": row.section_id,
        "block_id": getattr(row, "block_id", None) or "",
        "range_start": getattr(row, "range_start", None),
        "range_end": getattr(row, "range_end", None),
        "selected_text": getattr(row, "selected_text", None) or "",
        "evidence_ids": _json_loads(row.evidence_ids_json, []),
        "confidence_band": getattr(row, "confidence_band", None) or "",
        "recommendation": getattr(row, "recommendation", None) or "",
        "status": getattr(row, "status", None) or "open",
        "resolution_rationale": getattr(row, "resolution_rationale", None) or "",
        "resolved_at": resolved_at.isoformat() if resolved_at else None,
        "resolved_by": getattr(row, "resolved_by", None),
        "created_at": created_at.isoformat() if created_at else None,
    }


def serialize_run(row: Any, *, findings: list[Any] | None = None) -> dict[str, Any]:
    payload = {
        "id": row.id,
        "user_id": row.user_id,
        "project_id": row.project_id,
        "document_id": row.document_id,
        "document_version_no": int(row.document_version_no or 1),
        "writing_version": row.writing_version or "",
        "reviewer_version": row.reviewer_version or "",
        "binder_version": row.binder_version or "",
        "status": row.status,
        "pass_rate": float(row.pass_rate or 0.0),
        "sections_checked": int(row.sections_checked or 0),
        "sections_passed": int(row.sections_passed or 0),
        "issue_count": int(row.issue_count or 0),
        "metrics": _json_loads(row.metrics_json, {}),
        "input_snapshot": _json_loads(row.input_snapshot_json, {}),
        "model_version_id": row.model_version_id,
        "prompt_version_id": row.prompt_version_id,
        "prompt_meta": _json_loads(row.prompt_meta_json, {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }
    if findings is not None:
        payload["findings"] = [serialize_finding(f) for f in findings]
        # Reconstruct ReviewerResult-shaped review for clients that expect issues[].
        payload["review"] = {
            "reviewer_version": payload["reviewer_version"],
            "name": "research_reviewer",
            "status": payload["status"],
            "pass_rate": payload["pass_rate"],
            "sections_checked": payload["sections_checked"],
            "sections_passed": payload["sections_passed"],
            "issue_count": payload["issue_count"],
            "issues": [
                {
                    "code": f["code"],
                    "severity": f["severity"],
                    "section_id": f["section_id"],
                    "message": f["message"],
                    "evidence_ids": f["evidence_ids"],
                    "finding_id": f["id"],
                    "status": f["status"],
                }
                for f in payload["findings"]
            ],
            "metrics": payload["metrics"],
        }
    return payload
