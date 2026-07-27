"""Pipeline-internal issue tracking — never raised out of
DocumentUnderstandingPipeline.process() (see pipeline.py's module
docstring on the two-layer graceful-degradation design), never stored on
ProcessedDocument itself. pipeline.py accumulates StageIssues per stage
internally, then folds their messages into that stage's own StageLog
(models.py) and, for quality-relevant issues, into DocumentQuality.
warnings/errors — callers only ever see the flat string lists on those
two models, never this module's types directly.
"""

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class StageIssue:
    """One problem noticed during one pipeline stage.

    Attributes:
        stage: The stage name that raised/noticed this (e.g. "parser",
            "metadata") — matches StageLog.stage for the same run.
        severity: WARNING (stage produced a degraded-but-usable result)
            or ERROR (stage's own logic raised; a neutral default was
            substituted for its result).
        message: Human-readable, suitable to surface directly in
            DocumentQuality.warnings/errors or a StageLog.
    """

    stage: str
    severity: Severity
    message: str
