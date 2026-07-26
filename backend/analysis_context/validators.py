"""Input validation for AnalysisContextPipeline.process().

Same two-kind split as backend.classification.pass2.validators: passing
the wrong type at all is a caller bug (raised, not swallowed); a
structurally valid but thin/low-confidence ProcessedDocument or
ClassificationResult is an expected degradation case, surfaced as a
warning instead.
"""

from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

# Below this, classification's own decisions were themselves too
# uncertain for routing/prompt decisions built on top of them to be
# trustworthy — not a hard cutoff (this package still produces a full
# AnalysisContext), just a signal worth surfacing.
_MIN_CLASSIFICATION_CONFIDENCE_FOR_CONFIDENT_ROUTING = 0.3


def require_valid_inputs(document: ProcessedDocument, classification: ClassificationResult) -> None:
    """Raises TypeError if either argument isn't the type it claims to
    be — a caller bug, not a document/classification-quality problem, so
    this is allowed to raise rather than degrade gracefully."""
    if not isinstance(document, ProcessedDocument):
        raise TypeError(f"expected a ProcessedDocument, got {type(document).__name__}")
    if not isinstance(classification, ClassificationResult):
        raise TypeError(f"expected a ClassificationResult, got {type(classification).__name__}")


def validate_inputs(document: ProcessedDocument, classification: ClassificationResult) -> list[str]:
    """Returns human-readable warnings for structurally valid but thin or
    low-confidence inputs — never raises (see module docstring)."""
    warnings: list[str] = []

    if not document.full_text.strip():
        warnings.append("document has no extractable text; all profiles will be low-confidence")

    for decision, name in (
        (classification.document_type, "document_type"),
        (classification.domain, "domain"),
        (classification.study_design, "study_design"),
    ):
        if decision.confidence < _MIN_CLASSIFICATION_CONFIDENCE_FOR_CONFIDENT_ROUTING:
            warnings.append(
                f"classification.{name} confidence is low ({decision.confidence:.2f}); routing may be unreliable"
            )

    return warnings
