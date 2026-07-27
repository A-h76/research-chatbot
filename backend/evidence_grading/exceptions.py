"""Custom exceptions for the Evidence Grading Engine.

Internal-only vocabulary this package's own graceful-degradation layer
catches (see pipeline.py's module docstring) — never raised out of
EvidenceGradingPipeline.process() itself, never part of EvidenceGrades'
own public shape (that's ExtractionError/RecoveryAction in models.py,
built FROM these when caught).

SecurityError is the one exception a caller-supplied plugin_allowlist
violation raises for real (see security/isolation.py) — a deliberate,
policy-driven rejection, not a recoverable extraction failure, so it's
kept separate from the MedicalUnderstandingError-style hierarchy below
rather than folding it in as just another ErrorType.
"""

from typing import Optional

from .enums import ErrorSeverity, ErrorType, RecoveryType


class EvidenceGradingError(Exception):
    """Base class for every recoverable exception this package raises
    internally."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery_hint: Optional[RecoveryType] = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.recovery_hint = recovery_hint


class AssessmentFailedError(EvidenceGradingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.DEFAULT_ASSESSMENT) -> None:
        super().__init__(message, ErrorType.ASSESSMENT_ERROR, ErrorSeverity.ERROR, recovery_hint)


class FrameworkGradingError(EvidenceGradingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.SKIP_FRAMEWORK) -> None:
        super().__init__(message, ErrorType.FRAMEWORK_ERROR, ErrorSeverity.ERROR, recovery_hint)


class AggregationFailedError(EvidenceGradingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.CONSERVATIVE_GRADE) -> None:
        super().__init__(message, ErrorType.AGGREGATION_ERROR, ErrorSeverity.ERROR, recovery_hint)


class DependencyCycleError(EvidenceGradingError):
    """Raised when a grader/assessor's requires() graph contains a cycle
    — a configuration bug (someone registered a circular dependency), not
    a document-quality problem, so callers constructing an AssessmentPlan
    let this propagate rather than silently dropping nodes."""

    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.DEPENDENCY_ERROR, ErrorSeverity.CRITICAL)


class GradingTimeoutError(EvidenceGradingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.SKIP_FRAMEWORK) -> None:
        super().__init__(message, ErrorType.TIMEOUT_ERROR, ErrorSeverity.ERROR, recovery_hint)


class ResourceLimitExceededError(EvidenceGradingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.RESOURCE_LIMIT_ERROR, ErrorSeverity.CRITICAL)


class ConfidenceCalculationError(EvidenceGradingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.CONFIDENCE_ERROR, ErrorSeverity.ERROR)


class ValidationFailedError(EvidenceGradingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.VALIDATION_ERROR, ErrorSeverity.ERROR)


class SecurityError(Exception):
    """Raised when a plugin/grader name isn't in a non-empty
    plugin_allowlist (see security/isolation.py) — a policy rejection,
    deliberately not a subclass of EvidenceGradingError: it represents a
    configuration decision the caller made on purpose, not something to
    recover from automatically."""
