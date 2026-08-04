"""Auto-enqueue evidence_extract after Phase 1 (Paper Analysis 2.4).

Happy path: project assigned + research_ready → existing `evidence_extract` job.
No new job family. Idempotent with active-job skip; extract_service handles
content-hash reuse. Factory/DI — never `import server`.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.jobs.outbox import enqueue_upload_job_with_outbox
from backend.library.readiness import research_readiness

log = logging.getLogger(__name__)

_ACTIVE = ("pending", "running", "retry")


def find_active_evidence_extract_job(db, UploadJob: Any, file_id: int) -> Any | None:
    """Return pending/running/retry evidence_extract job for file, if any."""
    from sqlalchemy import select

    return db.execute(
        select(UploadJob).where(
            UploadJob.file_id == int(file_id),
            UploadJob.job_type == "evidence_extract",
            UploadJob.status.in_(_ACTIVE),
        )
    ).scalar_one_or_none()


def maybe_enqueue_evidence_extract(
    db,
    *,
    user_id: int,
    file_id: int,
    UserFile: Any,
    UploadJob: Any,
    OutboxEvent: Any,
    upload_batch_id: int | None = None,
    force: bool = False,
) -> Optional[int]:
    """Enqueue `evidence_extract` when gates pass. Returns job id or None.

    Gates:
    - UserFile exists and belongs to user_id
    - project_id set
    - research_readiness == research_ready
    - no active evidence_extract job for this file (unless force)
    """
    uf = db.get(UserFile, int(file_id))
    if not uf or int(uf.user_id) != int(user_id):
        return None
    if uf.project_id is None:
        log.debug("auto evidence_extract skip file=%s: no project", file_id)
        return None
    readiness = research_readiness(uf)
    if readiness != "research_ready":
        log.debug(
            "auto evidence_extract skip file=%s: readiness=%s",
            file_id,
            readiness,
        )
        return None

    if not force:
        active = find_active_evidence_extract_job(db, UploadJob, int(file_id))
        if active is not None:
            log.debug(
                "auto evidence_extract skip file=%s: active job=%s",
                file_id,
                getattr(active, "id", None),
            )
            return None

    job = enqueue_upload_job_with_outbox(
        db,
        UploadJob=UploadJob,
        OutboxEvent=OutboxEvent,
        user_id=int(user_id),
        file_id=int(file_id),
        job_type="evidence_extract",
        upload_batch_id=upload_batch_id,
        payload={
            "project_id": int(uf.project_id),
            "force": bool(force),
            "source": "auto_phase1",
            "already_applied": False,
        },
    )
    log.info(
        "auto evidence_extract enqueued file=%s project=%s job=%s",
        file_id,
        uf.project_id,
        job.id,
    )
    return int(job.id)
