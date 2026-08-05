"""Lightweight Research Workflow Engine (Bite 15).

Not agents. Not Celery. Not a second queue.

Research Workflow → Named Steps → State → Events

Advances on domain events + worker job outcomes. State is inspectable
via ``inspect`` / REST. Durable job execution remains ``worker.py`` + Postgres.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from backend.workflow.definitions import (
    JOB_TYPE_TO_STEP,
    RESEARCH_PAPER_STEPS,
    RESEARCH_PAPER_WORKFLOW,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STEP_EVIDENCE,
    STEP_IMPORT,
    STEP_REVIEW,
    STEP_SUE,
    STEP_UFTR,
    STEP_WRITING,
    WF_STATUS_ACTIVE,
    WORKFLOW_ENGINE_VERSION,
)
from backend.workflow.instance import WorkflowInstance, new_research_paper_instance
from backend.workflow.store import WorkflowStore

logger = logging.getLogger("backend.workflow.engine")


class WorkflowEngine:
    """Synchronous engine: ensure instance → mutate step state → log."""

    def __init__(self, store: WorkflowStore | None = None) -> None:
        self.store = store or WorkflowStore()
        self._lock = Lock()

    # ── inspect ───────────────────────────────────────────────────────

    def inspect(self, workflow_id: str) -> dict[str, Any] | None:
        inst = self.store.get(workflow_id)
        return inst.to_dict() if inst else None

    def inspect_file(self, user_id: int, file_id: int) -> dict[str, Any] | None:
        inst = self.store.get_by_file(user_id, file_id)
        return inst.to_dict() if inst else None

    def list_for_project(self, user_id: int, project_id: int) -> list[dict[str, Any]]:
        return [i.to_dict() for i in self.store.list_for_project(user_id, project_id)]

    # ── mutations ─────────────────────────────────────────────────────

    def ensure_research_paper(
        self,
        *,
        user_id: int,
        file_id: int,
        project_id: int | None = None,
        correlation_id: str | None = None,
    ) -> WorkflowInstance:
        with self._lock:
            existing = self.store.get_by_file(user_id, file_id)
            if existing is not None:
                if project_id is not None and existing.project_id is None:
                    existing.project_id = int(project_id)
                return existing
            inst = new_research_paper_instance(
                user_id=user_id,
                file_id=file_id,
                project_id=project_id,
                correlation_id=correlation_id,
            )
            self.store.put(inst)
            self._log(inst, action="started", step=None)
            return inst

    def begin_step(
        self,
        *,
        user_id: int,
        file_id: int,
        step: str,
        project_id: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        with self._lock:
            inst = self._require(user_id, file_id, project_id=project_id)
            st = inst.step(step)
            if st.status in (STATUS_COMPLETED, STATUS_SKIPPED):
                return inst
            from backend.workflow.instance import _utcnow

            st.status = STATUS_RUNNING
            st.started_at = st.started_at or _utcnow()
            if meta:
                st.meta.update(meta)
            inst.recompute_status()
            self.store.put(inst)
            self._log(inst, action="step_running", step=step)
            return inst

    def complete_step(
        self,
        *,
        user_id: int,
        file_id: int,
        step: str,
        project_id: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        with self._lock:
            inst = self._require(user_id, file_id, project_id=project_id)
            self._finish_step(inst, step, STATUS_COMPLETED, meta=meta)
            self._maybe_start_next(inst, step)
            self.store.put(inst)
            self._log(inst, action="step_completed", step=step)
            return inst

    def skip_step(
        self,
        *,
        user_id: int,
        file_id: int,
        step: str,
        project_id: int | None = None,
        reason: str = "",
        meta: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        with self._lock:
            inst = self._require(user_id, file_id, project_id=project_id)
            payload = dict(meta or {})
            if reason:
                payload["skip_reason"] = reason
            self._finish_step(inst, step, STATUS_SKIPPED, meta=payload)
            self._maybe_start_next(inst, step)
            self.store.put(inst)
            self._log(inst, action="step_skipped", step=step)
            return inst

    def fail_step(
        self,
        *,
        user_id: int,
        file_id: int,
        step: str,
        error: str,
        project_id: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        with self._lock:
            inst = self._require(user_id, file_id, project_id=project_id)
            st = inst.step(step)
            from backend.workflow.instance import _utcnow

            st.status = STATUS_FAILED
            st.error = (error or "")[:500]
            st.finished_at = _utcnow()
            if meta:
                st.meta.update(meta)
            inst.recompute_status()
            self.store.put(inst)
            self._log(inst, action="step_failed", step=step)
            return inst

    def complete_step_for_project(
        self,
        *,
        user_id: int,
        project_id: int,
        step: str,
        meta: dict[str, Any] | None = None,
    ) -> list[WorkflowInstance]:
        """Advance Writing/Review on all active file journeys in a project."""
        updated: list[WorkflowInstance] = []
        with self._lock:
            for inst in self.store.list_for_project(user_id, project_id):
                if inst.status != WF_STATUS_ACTIVE and step not in (
                    STEP_WRITING,
                    STEP_REVIEW,
                ):
                    continue
                if step not in inst.steps:
                    continue
                st = inst.step(step)
                if st.status in (STATUS_COMPLETED, STATUS_SKIPPED):
                    continue
                self._finish_step(inst, step, STATUS_COMPLETED, meta=meta)
                self._maybe_start_next(inst, step)
                self.store.put(inst)
                self._log(inst, action="step_completed", step=step)
                updated.append(inst)
        return updated

    # ── high-level notes (call sites) ─────────────────────────────────

    def note_paper_imported(
        self,
        *,
        user_id: int,
        file_id: int,
        project_id: int | None = None,
        source: str = "",
        has_held_pdf: bool = False,
    ) -> WorkflowInstance:
        """Import step done; UFTR running (or skipped when PDF already held)."""
        self.ensure_research_paper(
            user_id=user_id, file_id=file_id, project_id=project_id
        )
        self.complete_step(
            user_id=user_id,
            file_id=file_id,
            step=STEP_IMPORT,
            project_id=project_id,
            meta={"source": source},
        )
        if has_held_pdf:
            self.skip_step(
                user_id=user_id,
                file_id=file_id,
                step=STEP_UFTR,
                project_id=project_id,
                reason="held_pdf",
            )
            self.begin_step(
                user_id=user_id,
                file_id=file_id,
                step=STEP_SUE,
                project_id=project_id,
            )
        else:
            self.begin_step(
                user_id=user_id,
                file_id=file_id,
                step=STEP_UFTR,
                project_id=project_id,
            )
        return self.store.get_by_file(user_id, file_id)  # type: ignore[return-value]

    def note_uftr_result(
        self,
        *,
        user_id: int,
        file_id: int,
        project_id: int | None = None,
        pdf_attached: bool = False,
        analysis_queued: bool = False,
        pdf_error: str | None = None,
    ) -> WorkflowInstance | None:
        self.ensure_research_paper(
            user_id=user_id, file_id=file_id, project_id=project_id
        )
        meta = {
            "pdf_attached": bool(pdf_attached),
            "analysis_queued": bool(analysis_queued),
        }
        if pdf_error:
            meta["pdf_error"] = str(pdf_error)[:120]
        if pdf_attached or analysis_queued:
            self.complete_step(
                user_id=user_id,
                file_id=file_id,
                step=STEP_UFTR,
                project_id=project_id,
                meta=meta,
            )
            if analysis_queued:
                self.begin_step(
                    user_id=user_id,
                    file_id=file_id,
                    step=STEP_SUE,
                    project_id=project_id,
                )
        elif pdf_error:
            # Soft miss — skip UFTR (no PDF) rather than fail the whole journey.
            self.skip_step(
                user_id=user_id,
                file_id=file_id,
                step=STEP_UFTR,
                project_id=project_id,
                reason=str(pdf_error)[:80],
                meta=meta,
            )
        return self.store.get_by_file(user_id, file_id)

    def note_job_outcome(
        self,
        *,
        user_id: int,
        file_id: int | None,
        job_type: str,
        outcome: str,
        project_id: int | None = None,
        error: str | None = None,
    ) -> WorkflowInstance | None:
        """Map worker job_type → step (import / SUE / Evidence)."""
        if file_id is None:
            return None
        step = JOB_TYPE_TO_STEP.get(job_type)
        if not step:
            return None
        self.ensure_research_paper(
            user_id=user_id, file_id=file_id, project_id=project_id
        )
        if outcome == "done":
            # Import job after held-bytes: Import may already be completed.
            if step == STEP_IMPORT:
                inst = self.store.get_by_file(user_id, file_id)
                if inst and inst.step(STEP_IMPORT).status == STATUS_COMPLETED:
                    return inst
            self.complete_step(
                user_id=user_id,
                file_id=file_id,
                step=step,
                project_id=project_id,
                meta={"job_type": job_type},
            )
            if step == STEP_SUE:
                self.begin_step(
                    user_id=user_id,
                    file_id=file_id,
                    step=STEP_EVIDENCE,
                    project_id=project_id,
                )
            elif step == STEP_EVIDENCE:
                self.begin_step(
                    user_id=user_id,
                    file_id=file_id,
                    step=STEP_WRITING,
                    project_id=project_id,
                )
            return self.store.get_by_file(user_id, file_id)
        if outcome == "failed":
            return self.fail_step(
                user_id=user_id,
                file_id=file_id,
                step=step,
                error=error or "job_failed",
                project_id=project_id,
                meta={"job_type": job_type},
            )
        return None

    def note_writing_generated(
        self,
        *,
        user_id: int,
        project_id: int | None,
        execution_id: str | None = None,
    ) -> list[WorkflowInstance]:
        if project_id is None:
            return []
        return self.complete_step_for_project(
            user_id=user_id,
            project_id=project_id,
            step=STEP_WRITING,
            meta={"execution_id": execution_id} if execution_id else None,
        )

    def note_review_recorded(
        self,
        *,
        user_id: int,
        project_id: int | None,
        evidence_id: int | None = None,
        decision_type: str = "",
    ) -> list[WorkflowInstance]:
        if project_id is None:
            return []
        meta: dict[str, Any] = {"decision_type": decision_type}
        if evidence_id is not None:
            meta["evidence_id"] = int(evidence_id)
        return self.complete_step_for_project(
            user_id=user_id,
            project_id=project_id,
            step=STEP_REVIEW,
            meta=meta,
        )

    # ── internals ─────────────────────────────────────────────────────

    def _require(
        self,
        user_id: int,
        file_id: int,
        *,
        project_id: int | None = None,
    ) -> WorkflowInstance:
        inst = self.store.get_by_file(user_id, file_id)
        if inst is None:
            inst = new_research_paper_instance(
                user_id=user_id, file_id=file_id, project_id=project_id
            )
            self.store.put(inst)
        elif project_id is not None and inst.project_id is None:
            inst.project_id = int(project_id)
        return inst

    def _finish_step(
        self,
        inst: WorkflowInstance,
        step: str,
        status: str,
        *,
        meta: dict[str, Any] | None = None,
    ) -> None:
        from backend.workflow.instance import _utcnow

        st = inst.step(step)
        if st.status in (STATUS_COMPLETED, STATUS_SKIPPED) and status in (
            STATUS_COMPLETED,
            STATUS_SKIPPED,
        ):
            if meta:
                st.meta.update(meta)
            return
        st.status = status
        st.finished_at = _utcnow()
        if st.started_at is None:
            st.started_at = st.finished_at
        st.error = None
        if meta:
            st.meta.update(meta)
        inst.recompute_status()

    def _maybe_start_next(self, inst: WorkflowInstance, completed_step: str) -> None:
        order = list(RESEARCH_PAPER_STEPS)
        try:
            idx = order.index(completed_step)
        except ValueError:
            return
        for name in order[idx + 1 :]:
            st = inst.step(name)
            if st.status == STATUS_PENDING:
                from backend.workflow.instance import _utcnow

                st.status = STATUS_RUNNING
                st.started_at = _utcnow()
                return
            if st.status == STATUS_RUNNING:
                return
            # completed/skipped → keep looking
            continue

    def _log(self, inst: WorkflowInstance, *, action: str, step: str | None) -> None:
        logger.info(
            "research_workflow",
            extra={
                "research_workflow": {
                    "engine_version": WORKFLOW_ENGINE_VERSION,
                    "action": action,
                    "step": step,
                    "workflow_id": inst.workflow_id,
                    "workflow_name": inst.workflow_name,
                    "user_id": inst.user_id,
                    "file_id": inst.file_id,
                    "project_id": inst.project_id,
                    "status": inst.status,
                    "current_step": inst.current_step(),
                    "steps": {n: s.status for n, s in inst.steps.items()},
                }
            },
        )


_engine: WorkflowEngine | None = None
_engine_lock = Lock()


def get_engine() -> WorkflowEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = WorkflowEngine()
        return _engine


def set_engine(engine: WorkflowEngine | None) -> None:
    global _engine
    with _engine_lock:
        _engine = engine


def clear_engine_for_tests() -> None:
    eng = get_engine()
    eng.store.clear()
