"""Phase 2 Analysis Pipeline Integration.

Orchestrates Phase 1.1–1.7 as black-box libraries, persists results, and
exposes one service used by the worker and HTTP paths.

Correct Phase 1 order (plan's 1.4/1.5 labels were swapped vs the repo):
  1.1 Document Understanding
  1.2 Classification (pass2)
  1.3 Analysis Context
  1.4 Medical Understanding
  1.5 Evidence Grading
  1.6 Prompt Assembly
  1.7 Knowledge Graph

Non-goals: Phase 1 rewrites, Celery (Postgres worker stays), new AI algorithms.
"""

from .models import AnalysisOptions, AnalysisResult, AnalysisJobStatus
from .service import AnalysisPipelineService, PIPELINE_VERSION

__all__ = [
    "AnalysisPipelineService",
    "AnalysisOptions",
    "AnalysisResult",
    "AnalysisJobStatus",
    "PIPELINE_VERSION",
]
