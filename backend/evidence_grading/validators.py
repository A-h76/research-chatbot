"""Input and output validation for EvidenceGradingPipeline.process().

Same two-kind split every prior phase's validators.py uses: passing the
wrong type at all is a caller bug (raised, not swallowed); anything else
thin/low-confidence/over-limit is an expected degradation case, surfaced
as a warning instead.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from .config import EvidenceGradingConfig
from .models import EvidenceGrades


def require_valid_inputs(
    document: ProcessedDocument,
    classification: ClassificationResult,
    context: AnalysisContext,
    medical: MedicalUnderstanding,
) -> None:
    """Raises TypeError if any argument isn't the type it claims to be —
    a caller bug, not a document-quality problem."""
    if not isinstance(document, ProcessedDocument):
        raise TypeError(f"expected a ProcessedDocument, got {type(document).__name__}")
    if not isinstance(classification, ClassificationResult):
        raise TypeError(f"expected a ClassificationResult, got {type(classification).__name__}")
    if not isinstance(context, AnalysisContext):
        raise TypeError(f"expected an AnalysisContext, got {type(context).__name__}")
    if not isinstance(medical, MedicalUnderstanding):
        raise TypeError(f"expected a MedicalUnderstanding, got {type(medical).__name__}")


def validate_inputs(
    document: ProcessedDocument,
    classification: ClassificationResult,
    medical: MedicalUnderstanding,
) -> list[str]:
    """Returns human-readable warnings for structurally valid but thin
    inputs — never raises (see module docstring)."""
    warnings: list[str] = []

    if medical.skipped:
        warnings.append("medical understanding was itself skipped; evidence grading will have little to work with")
    if not medical.clinical_entities and not medical.statistical_measures:
        warnings.append("no clinical entities or statistical measures were extracted; assessments will be low-confidence")
    if classification.study_design.confidence < 0.3:
        warnings.append(
            f"study_design classification confidence is low ({classification.study_design.confidence:.2f}); "
            "framework selection may be unreliable"
        )

    return warnings


def validate_output(grades: EvidenceGrades, config: EvidenceGradingConfig) -> list[str]:
    """Returns warnings about the assembled EvidenceGrades itself — e.g.
    limits that were actually hit — never raises or mutates the result."""
    warnings: list[str] = []

    if len(grades.outcome_grades) >= config.max_outcomes:
        warnings.append(f"outcome grade count reached the configured limit ({config.max_outcomes}); results may be truncated")

    if not 0.0 <= grades.confidence.overall <= 1.0:
        warnings.append(f"overall confidence {grades.confidence.overall} is outside the valid [0, 1] range")

    return warnings
