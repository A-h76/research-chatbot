"""Custom exceptions for the Medical Understanding Engine.

Internal-only vocabulary this package's own graceful-degradation layer
catches (see pipeline.py's module docstring) — never raised out of
MedicalUnderstandingPipeline.process() itself, never part of
MedicalUnderstanding's own public shape (that's ExtractionError/
RecoveryAction in models.py, built FROM these when caught).

Each carries an optional `recovery_hint` (a RecoveryType) — the
"...with recovery" the task's own directory tree names this file for:
the raise site's best guess at which RecoveryAction the catching layer
should attempt (e.g. an extractor whose methods-section text failed to
parse hints ABSTRACT_FALLBACK, since the abstract usually restates the
same facts less precisely) — advisory only, the catching layer decides
whether to actually attempt it.
"""

from typing import Optional

from .enums import ErrorSeverity, ErrorType, RecoveryType


class MedicalUnderstandingError(Exception):
    """Base class for every exception this package raises internally."""

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


class ExtractionFailedError(MedicalUnderstandingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.ABSTRACT_FALLBACK) -> None:
        super().__init__(message, ErrorType.EXTRACTION_ERROR, ErrorSeverity.ERROR, recovery_hint)


class NormalizationFailedError(MedicalUnderstandingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.NORMALIZATION) -> None:
        super().__init__(message, ErrorType.NORMALIZATION_ERROR, ErrorSeverity.WARNING, recovery_hint)


class OntologyLookupError(MedicalUnderstandingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.PATTERN_ALTERNATIVE) -> None:
        super().__init__(message, ErrorType.ONTOLOGY_LOOKUP_ERROR, ErrorSeverity.WARNING, recovery_hint)


class ConfidenceCalculationError(MedicalUnderstandingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.CONFIDENCE_ERROR, ErrorSeverity.ERROR)


class ExtractionTimeoutError(MedicalUnderstandingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.PATTERN_ALTERNATIVE) -> None:
        super().__init__(message, ErrorType.TIMEOUT_ERROR, ErrorSeverity.ERROR, recovery_hint)


class ResourceLimitExceededError(MedicalUnderstandingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.MEMORY_LIMIT_ERROR, ErrorSeverity.CRITICAL)


class UnsafeRegexError(MedicalUnderstandingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.REGEX_ERROR, ErrorSeverity.ERROR)


class DocumentParseError(MedicalUnderstandingError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.TITLE_FALLBACK) -> None:
        super().__init__(message, ErrorType.PARSE_ERROR, ErrorSeverity.ERROR, recovery_hint)


class ValidationFailedError(MedicalUnderstandingError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.VALIDATION_ERROR, ErrorSeverity.ERROR)
