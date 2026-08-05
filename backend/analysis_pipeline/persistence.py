"""Persistence helpers for analysis_pipeline_results (injected ORM)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from .models import AnalysisJobStatus, AnalysisResult


def save_analysis_result(db, AnalysisPipelineResult, result: AnalysisResult, *, user_id: int) -> Any:
    """Upsert one row per file_id."""
    from sqlalchemy import select

    row = db.execute(
        select(AnalysisPipelineResult).where(AnalysisPipelineResult.file_id == result.file_id)
    ).scalar_one_or_none()
    if row is None:
        row = AnalysisPipelineResult(file_id=result.file_id, user_id=user_id)
        db.add(row)

    row.user_id = user_id
    row.content_hash = result.content_hash
    row.status = result.status.value
    row.error = "; ".join(result.errors)[:2000] if result.errors else ""
    row.phase_results = json.dumps(result.phase_results, ensure_ascii=False)
    row.pipeline_version = result.pipeline_version
    row.total_processing_time_ms = int(result.total_processing_time_ms)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return row


def load_analysis_result(db, AnalysisPipelineResult, file_id: int) -> Optional[AnalysisResult]:
    from sqlalchemy import select

    row = db.execute(
        select(AnalysisPipelineResult).where(AnalysisPipelineResult.file_id == file_id)
    ).scalar_one_or_none()
    if row is None:
        return None
    try:
        phases = json.loads(row.phase_results or "{}")
    except json.JSONDecodeError:
        phases = {}
    try:
        status = AnalysisJobStatus(row.status)
    except ValueError:
        status = AnalysisJobStatus.FAILED
    return AnalysisResult(
        file_id=row.file_id,
        content_hash=row.content_hash or "",
        status=status,
        phase_results=phases,
        pipeline_version=row.pipeline_version or "",
        total_processing_time_ms=float(row.total_processing_time_ms or 0),
        errors=[row.error] if row.error else [],
        created_at=row.created_at or datetime.now(timezone.utc),
        updated_at=getattr(row, "updated_at", None) or row.created_at,
    )


def apply_metadata_to_user_file(uf, fields: dict[str, str], *, only_empty: bool = True) -> bool:
    """Write bibliographic fields onto UserFile. Returns True if any field changed."""
    changed = False
    for attr, value in fields.items():
        if not value:
            continue
        current = getattr(uf, attr, None) or ""
        if only_empty and current:
            continue
        setattr(uf, attr, value)
        changed = True
    if changed:
        uf.meta_status = "done"
    return changed
