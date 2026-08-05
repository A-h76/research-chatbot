"""Workflow instance + step state value types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.workflow.definitions import (
    RESEARCH_PAPER_STEPS,
    RESEARCH_PAPER_WORKFLOW,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SKIPPED,
    WF_STATUS_ACTIVE,
    WF_STATUS_COMPLETED,
    WF_STATUS_FAILED,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepState:
    name: str
    status: str = STATUS_PENDING
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "meta": dict(self.meta),
        }


@dataclass
class WorkflowInstance:
    """One inspectable research journey (typically one library file)."""

    workflow_id: str
    workflow_name: str
    user_id: int
    file_id: int | None
    project_id: int | None
    steps: dict[str, StepState]
    status: str = WF_STATUS_ACTIVE
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)
    correlation_id: str | None = None

    def step(self, name: str) -> StepState:
        if name not in self.steps:
            raise KeyError(f"unknown step {name!r} for workflow {self.workflow_name}")
        return self.steps[name]

    def ordered_steps(self) -> list[StepState]:
        order = RESEARCH_PAPER_STEPS if self.workflow_name == RESEARCH_PAPER_WORKFLOW else tuple(self.steps)
        return [self.steps[n] for n in order if n in self.steps]

    def current_step(self) -> str | None:
        for s in self.ordered_steps():
            if s.status not in (STATUS_COMPLETED, STATUS_SKIPPED):
                return s.name
        return None

    def recompute_status(self) -> None:
        vals = [s.status for s in self.steps.values()]
        if any(v == STATUS_FAILED for v in vals):
            self.status = WF_STATUS_FAILED
        elif all(v in (STATUS_COMPLETED, STATUS_SKIPPED) for v in vals):
            self.status = WF_STATUS_COMPLETED
        else:
            self.status = WF_STATUS_ACTIVE
        self.updated_at = _utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "user_id": self.user_id,
            "file_id": self.file_id,
            "project_id": self.project_id,
            "status": self.status,
            "current_step": self.current_step(),
            "steps": [s.to_dict() for s in self.ordered_steps()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "correlation_id": self.correlation_id,
        }


def new_research_paper_instance(
    *,
    user_id: int,
    file_id: int,
    project_id: int | None = None,
    correlation_id: str | None = None,
) -> WorkflowInstance:
    workflow_id = f"rw:{int(user_id)}:file:{int(file_id)}"
    steps = {name: StepState(name=name) for name in RESEARCH_PAPER_STEPS}
    return WorkflowInstance(
        workflow_id=workflow_id,
        workflow_name=RESEARCH_PAPER_WORKFLOW,
        user_id=int(user_id),
        file_id=int(file_id),
        project_id=int(project_id) if project_id is not None else None,
        steps=steps,
        correlation_id=correlation_id,
    )
