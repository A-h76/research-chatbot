"""Custom exceptions for the Prompt Assembly Engine.

Internal-only — pipeline.process() catches builder/assembly failures and
records ExtractionError entries; only ValidationError for wrong argument
types propagates to the caller (mirroring Phase 1.4/1.5).
"""

from typing import Optional

from .enums import ErrorSeverity, ErrorType, RecoveryType


class PromptAssemblyError(Exception):
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


class ValidationError(PromptAssemblyError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.VALIDATION_ERROR, ErrorSeverity.CRITICAL)


class BuilderFailedError(PromptAssemblyError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.SKIP_COMPONENT) -> None:
        super().__init__(message, ErrorType.BUILDER_ERROR, ErrorSeverity.ERROR, recovery_hint)


class AssemblyFailedError(PromptAssemblyError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.FALLBACK_TEMPLATE) -> None:
        super().__init__(message, ErrorType.ASSEMBLY_ERROR, ErrorSeverity.ERROR, recovery_hint)


class TemplateError(PromptAssemblyError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.FALLBACK_TEMPLATE) -> None:
        super().__init__(message, ErrorType.TEMPLATE_ERROR, ErrorSeverity.ERROR, recovery_hint)


class TokenLimitError(PromptAssemblyError):
    def __init__(self, message: str, recovery_hint: Optional[RecoveryType] = RecoveryType.TRUNCATE_CONTENT) -> None:
        super().__init__(message, ErrorType.TOKEN_LIMIT_ERROR, ErrorSeverity.WARNING, recovery_hint)


class SecurityError(PromptAssemblyError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorType.SECURITY_ERROR, ErrorSeverity.CRITICAL)
