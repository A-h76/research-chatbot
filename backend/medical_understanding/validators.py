"""Input and output validation for MedicalUnderstandingPipeline.process().

Same two-kind split every prior phase's validators.py uses: passing the
wrong type at all is a caller bug (raised, not swallowed); anything else
thin/low-confidence/over-limit is an expected degradation case, surfaced
as a warning instead.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .config import MedicalUnderstandingConfig
from .models import MedicalUnderstanding


def require_valid_inputs(
    document: ProcessedDocument, classification: ClassificationResult, context: AnalysisContext
) -> None:
    """Raises TypeError if any argument isn't the type it claims to be —
    a caller bug, not a document-quality problem."""
    if not isinstance(document, ProcessedDocument):
        raise TypeError(f"expected a ProcessedDocument, got {type(document).__name__}")
    if not isinstance(classification, ClassificationResult):
        raise TypeError(f"expected a ClassificationResult, got {type(classification).__name__}")
    if not isinstance(context, AnalysisContext):
        raise TypeError(f"expected an AnalysisContext, got {type(context).__name__}")


def validate_inputs(
    document: ProcessedDocument, classification: ClassificationResult, context: AnalysisContext
) -> list[str]:
    """Returns human-readable warnings for structurally valid but thin
    inputs — never raises (see module docstring)."""
    warnings: list[str] = []
    if not document.full_text.strip():
        warnings.append("document has no extractable text; extraction will find nothing")
    if context.quality_profile.reliability_score < 0.4:
        warnings.append(
            f"analysis context reliability is low ({context.quality_profile.reliability_score:.2f}); "
            "extraction confidence may be unreliable"
        )
    return warnings


def validate_output(understanding: MedicalUnderstanding, config: MedicalUnderstandingConfig) -> list[str]:
    """Returns warnings about the assembled MedicalUnderstanding itself
    — e.g. limits that were actually hit — never raises or mutates the
    result; callers decide what (if anything) to do with these."""
    warnings: list[str] = []

    total_entities = len(understanding.clinical_entities)
    if total_entities >= config.max_entities:
        warnings.append(f"entity count reached the configured limit ({config.max_entities}); results may be truncated")

    if not 0.0 <= understanding.confidence.overall <= 1.0:
        warnings.append(f"overall confidence {understanding.confidence.overall} is outside the valid [0, 1] range")

    return warnings
