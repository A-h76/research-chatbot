"""PaperAnalysis status helpers — cross-paper research readiness gate.

Project research (``backend/projects/research.py``) requires
``PaperAnalysis.status == "done"``. Upload ``meta_status`` alone is not
sufficient; these helpers expose the same rule on file list + hub payloads.
"""

from __future__ import annotations

from typing import Any

_VALID_STATUSES = frozenset({"pending", "running", "done", "failed"})


def normalize_analysis_status(status: str | None) -> str:
    s = (status or "pending").lower()
    return s if s in _VALID_STATUSES else "pending"


def cross_paper_research_ready(status: str | None) -> bool:
    return normalize_analysis_status(status) == "done"


def batch_paper_analysis_status(
    db: Any,
    file_ids: list[int],
    PaperAnalysis: Any,
    select_fn: Any,
) -> dict[int, str]:
    """Map file_id → analysis status (missing row ⇒ pending)."""
    ids = [int(i) for i in file_ids if i]
    if not ids:
        return {}
    rows = db.execute(
        select_fn(PaperAnalysis.file_id, PaperAnalysis.status).where(
            PaperAnalysis.file_id.in_(ids)
        )
    ).all()
    out = {int(fid): normalize_analysis_status(status) for fid, status in rows}
    for fid in ids:
        out.setdefault(fid, "pending")
    return out


def enrich_file_payload(payload: dict[str, Any], analysis_status: str) -> dict[str, Any]:
    status = normalize_analysis_status(analysis_status)
    payload["paper_analysis_status"] = status
    payload["cross_paper_research_ready"] = cross_paper_research_ready(status)
    return payload
