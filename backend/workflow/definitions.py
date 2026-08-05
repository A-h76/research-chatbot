"""Canonical Research Workflow step definitions (Bite 15).

Not agents. A research paper journey is a named pipeline of steps with
inspectable state. Domain events and worker stages advance steps.
"""

from __future__ import annotations

WORKFLOW_ENGINE_VERSION = "1.0"

# Canonical paper research journey — every acquisition path should land here.
RESEARCH_PAPER_WORKFLOW = "research_paper"

STEP_IMPORT = "Import"
STEP_UFTR = "UFTR"
STEP_SUE = "SUE"
STEP_EVIDENCE = "Evidence"
STEP_WRITING = "Writing"
STEP_REVIEW = "Review"

RESEARCH_PAPER_STEPS: tuple[str, ...] = (
    STEP_IMPORT,
    STEP_UFTR,
    STEP_SUE,
    STEP_EVIDENCE,
    STEP_WRITING,
    STEP_REVIEW,
)

# Terminal / progress statuses for a single step.
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

STEP_STATUSES = frozenset(
    {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_COMPLETED,
        STATUS_SKIPPED,
        STATUS_FAILED,
    }
)

# Whole-workflow status derived from steps.
WF_STATUS_ACTIVE = "active"
WF_STATUS_COMPLETED = "completed"
WF_STATUS_FAILED = "failed"

# Worker job_type → workflow step (existing Postgres queue — ADR-0001).
JOB_TYPE_TO_STEP: dict[str, str] = {
    "import": STEP_IMPORT,
    "phase1_analysis": STEP_SUE,
    "paper_analysis": STEP_SUE,
    "evidence_extract": STEP_EVIDENCE,
}
