"""Input and output validation for PromptAssemblyPipeline."""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from .config import PromptAssemblyConfig
from .exceptions import ValidationError
from .models import AssembledPrompt


def require_valid_inputs(
    document: ProcessedDocument,
    classification: ClassificationResult,
    context: AnalysisContext,
    medical: MedicalUnderstanding,
    grades: EvidenceGrades,
) -> None:
    if not isinstance(document, ProcessedDocument):
        raise ValidationError(f"document must be ProcessedDocument, got {type(document).__name__}")
    if not isinstance(classification, ClassificationResult):
        raise ValidationError(f"classification must be ClassificationResult, got {type(classification).__name__}")
    if not isinstance(context, AnalysisContext):
        raise ValidationError(f"context must be AnalysisContext, got {type(context).__name__}")
    if not isinstance(medical, MedicalUnderstanding):
        raise ValidationError(f"medical must be MedicalUnderstanding, got {type(medical).__name__}")
    if not isinstance(grades, EvidenceGrades):
        raise ValidationError(f"grades must be EvidenceGrades, got {type(grades).__name__}")


def validate_inputs(
    document: ProcessedDocument,
    medical: MedicalUnderstanding,
    grades: EvidenceGrades,
) -> list[str]:
    warnings: list[str] = []
    if not (document.metadata.title or "").strip() and not (document.full_text or "").strip():
        warnings.append("document has empty title and full_text")
    if medical.skipped:
        warnings.append(f"medical understanding skipped: {medical.reasoning or 'no reason'}")
    if grades.skipped:
        warnings.append(f"evidence grades skipped: {grades.reasoning or 'no reason'}")
    return warnings


def validate_output(prompt: AssembledPrompt, config: PromptAssemblyConfig) -> list[str]:
    warnings: list[str] = []
    if not prompt.system_prompt.strip():
        warnings.append("assembled system_prompt is empty")
    if not prompt.user_prompt.strip():
        warnings.append("assembled user_prompt is empty")
    if len(prompt.full_prompt) > config.max_prompt_length:
        warnings.append(
            f"full_prompt length {len(prompt.full_prompt)} exceeds max_prompt_length {config.max_prompt_length}"
        )
    if prompt.assembly_log.tokens_estimated > config.max_total_prompt_tokens:
        warnings.append(
            f"estimated tokens {prompt.assembly_log.tokens_estimated} exceed "
            f"max_total_prompt_tokens {config.max_total_prompt_tokens}"
        )
    if not (0.0 <= prompt.confidence_score.overall <= 1.0):
        warnings.append(f"confidence overall out of range: {prompt.confidence_score.overall}")
    return warnings
