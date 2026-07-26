"""Closed label sets for the Prompt Assembly Engine (Phase 1.6).

PromptFamily and PromptStrategy are reused from
backend.analysis_context.enums (Phase 1.3) — see package docstring.
EVIDENCE_BASED and PICO_FIRST were added there additively for this
phase; this module re-exports them so callers can import from either
package.

PromptComponentType / PromptPriority / TokenEstimationStrategy /
ErrorType / ErrorSeverity / RecoveryType are this phase's own.
"""

from enum import Enum

from backend.analysis_context.enums import PromptFamily, PromptStrategy

__all__ = [
    "PromptFamily",
    "PromptStrategy",
    "PromptComponentType",
    "PromptPriority",
    "TokenEstimationStrategy",
    "ErrorType",
    "ErrorSeverity",
    "RecoveryType",
]


class PromptComponentType(str, Enum):
    SYSTEM_INSTRUCTION = "system_instruction"
    TASK_DESCRIPTION = "task_description"
    DOCUMENT_CONTEXT = "document_context"
    EVIDENCE = "evidence"
    PICO = "pico"
    CLINICAL_ENTITIES = "clinical_entities"
    STATISTICS = "statistics"
    GRADING = "grading"
    INSTRUCTION = "instruction"
    QUESTION = "question"
    OUTPUT_FORMAT = "output_format"


class PromptPriority(str, Enum):
    CRITICAL = "critical"  # Must include (bypasses confidence filter)
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class TokenEstimationStrategy(str, Enum):
    WORD_COUNT = "word_count"  # ~0.75 words per token
    CHARACTER_COUNT = "character_count"  # ~4 chars per token
    TIKTOKEN = "tiktoken"  # optional; falls back to HYBRID if unavailable
    HYBRID = "hybrid"  # max(word, char) — conservative


class ErrorType(str, Enum):
    VALIDATION_ERROR = "validation_error"
    BUILDER_ERROR = "builder_error"
    ASSEMBLY_ERROR = "assembly_error"
    TEMPLATE_ERROR = "template_error"
    TOKEN_LIMIT_ERROR = "token_limit_error"
    SECURITY_ERROR = "security_error"
    CONFIDENCE_ERROR = "confidence_error"


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RecoveryType(str, Enum):
    FALLBACK_TEMPLATE = "fallback_template"
    SKIP_COMPONENT = "skip_component"
    TRUNCATE_CONTENT = "truncate_content"
    DEFAULT_STRATEGY = "default_strategy"
    RETRY = "retry"
