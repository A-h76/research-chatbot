"""Integration-layer models (not Phase 1 models)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AnalysisJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class AnalysisOptions:
    """Controls which Phase 1 stages run. Defaults run the full chain."""

    run_classification: bool = True
    run_analysis_context: bool = True
    run_medical: bool = True
    run_evidence_grading: bool = True
    run_prompt_assembly: bool = True
    run_knowledge_graph: bool = True
    # Truncate large text fields before JSON persistence
    max_full_text_chars: int = 100_000
    persist_graph_formats: bool = False
    force: bool = False  # ignore content_hash cache


@dataclass
class AnalysisResult:
    """Persisted + in-memory outcome of one analyze_document call."""

    file_id: int
    content_hash: str
    status: AnalysisJobStatus
    phase_results: dict[str, Any] = field(default_factory=dict)
    pipeline_version: str = ""
    total_processing_time_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    def phase(self, name: str) -> Any:
        return self.phase_results.get(name)

    def to_api_dict(self) -> dict[str, Any]:
        stamp = self.updated_at or self.created_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return {
            "file_id": self.file_id,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "pipeline_version": self.pipeline_version,
            "total_processing_time_ms": self.total_processing_time_ms,
            "warnings": self.warnings,
            "errors": self.errors,
            "phases": list(self.phase_results.keys()),
            "phase_results": self.phase_results,
            "updated_at": stamp.isoformat().replace("+00:00", "Z"),
        }
