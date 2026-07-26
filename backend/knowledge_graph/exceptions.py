"""Custom exceptions for the Knowledge Graph Engine."""

from typing import Optional

from .enums import ErrorSeverity, ErrorType, RecoveryType


class KnowledgeGraphError(Exception):
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


class ValidationError(KnowledgeGraphError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.VALIDATION_ERROR, ErrorSeverity.CRITICAL)


class BuilderFailedError(KnowledgeGraphError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.SKIP_BUILDER) -> None:
        super().__init__(message, ErrorType.BUILDER_ERROR, ErrorSeverity.ERROR, recovery_hint)


class MergeFailedError(KnowledgeGraphError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.MERGE_ERROR, ErrorSeverity.ERROR, RecoveryType.TRUNCATE_GRAPH)


class SerializationError(KnowledgeGraphError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.SERIALIZATION_ERROR, ErrorSeverity.WARNING)


class SecurityError(KnowledgeGraphError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.SECURITY_ERROR, ErrorSeverity.CRITICAL)


class ResourceLimitError(KnowledgeGraphError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.RESOURCE_LIMIT_ERROR, ErrorSeverity.WARNING, RecoveryType.TRUNCATE_GRAPH)
