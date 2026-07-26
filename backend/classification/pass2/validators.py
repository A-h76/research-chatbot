"""Input validation for DocumentClassificationPipeline.process().

Two different kinds of "invalid", handled differently (same split as
backend.document_understanding.pipeline's own module docstring): passing
something that isn't a ProcessedDocument at all is a caller bug — raised
immediately, not swallowed. A ProcessedDocument that's simply thin (no
extractable text, no title) is a normal, expected degradation case from
Phase 1.1 — not an error, just something worth a warning so a low-
confidence classification isn't mistaken for a confident one.
"""

from backend.document_understanding.models import ProcessedDocument

# Below this many characters, keyword/venue matching has too little text
# to be meaningful — not a hard cutoff for "don't classify" (a detector
# may still find e.g. a venue match), just a signal worth surfacing.
_MIN_TEXT_LENGTH_FOR_CONFIDENT_CLASSIFICATION = 50


def require_processed_document(document: ProcessedDocument) -> None:
    """Raises TypeError if `document` isn't a ProcessedDocument — a
    caller bug (wrong type passed in), not a document-quality problem,
    so this is allowed to raise rather than degrade gracefully."""
    if not isinstance(document, ProcessedDocument):
        raise TypeError(f"expected a ProcessedDocument, got {type(document).__name__}")


def validate_document(document: ProcessedDocument) -> list[str]:
    """Returns human-readable warnings for a structurally valid but thin
    ProcessedDocument — never raises (see module docstring)."""
    warnings: list[str] = []

    if len(document.full_text.strip()) < _MIN_TEXT_LENGTH_FOR_CONFIDENT_CLASSIFICATION:
        warnings.append(
            "document has very little extractable text "
            f"({len(document.full_text.strip())} character(s)); classification confidence will be low"
        )

    if not document.metadata.title and not document.metadata.abstract:
        warnings.append("document has no title and no abstract; classification relies on full_text alone")

    return warnings
