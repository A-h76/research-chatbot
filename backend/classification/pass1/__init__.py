"""Pass 1 Classification — Document Understanding.

    ProcessedDocument
        |
        v
    DomainClassifier            (domain.py)
        |
        v
    DocumentTypeClassifier      (type.py)
        |
        v
    PublicationTypeClassifier   (publication.py)  -- uses document_type as an extra signal
        |
        v
    DocumentUnderstanding       (models.py)

Each classifier is independently usable and constructor-free (no
dependency injection needed — see rules.py's module docstring: everything
here is deterministic keyword/venue/structural matching, no DB/network
dependency of any kind). classify_document() below is a thin convenience
that runs all three in the order the diagram shows and assembles the
final DocumentUnderstanding; nothing requires calling it that way — a
caller that only wants, say, domain classification can use DomainClassifier
directly.

Non-goals (see the task this package was built under): ML/LLM-based
classification (every classifier here is deterministic rule matching, on
purpose — ModelRegistry-backed classifiers are a future extension,
implementing the same *Classifier.classify() interface, not a change to
these), complex NLP (no tokenization/parsing beyond substring matching).

Extensibility (no core pipeline logic changes needed for any of these):
  - New domain: add it to models.DOMAINS and keywords.DOMAIN_KEYWORDS/
    DOMAIN_VENUES.
  - New document type: add it to models.DOCUMENT_TYPES and
    keywords.DOCUMENT_TYPE_KEYWORDS (optionally
    DOCUMENT_TYPE_STRUCTURAL_FEATURES).
  - New publication type: add it to models.PUBLICATION_TYPES and
    keywords.PUBLICATION_TYPE_VENUES/PUBLICATION_TYPE_KEYWORDS.
  - New signal source for any classifier: a new match_*() function in
    rules.py, folded into that classifier's combine_signals() call.
"""

from backend.processing.models import ProcessedDocument

from .domain import DomainClassifier
from .models import (
    DOCUMENT_TYPES,
    DOMAINS,
    PUBLICATION_TYPES,
    DocumentTypeClassificationResult,
    DocumentUnderstanding,
    DomainClassificationResult,
    PublicationTypeClassificationResult,
)
from .publication import PublicationTypeClassifier
from .type import DocumentTypeClassifier

__all__ = [
    "DOMAINS",
    "DOCUMENT_TYPES",
    "PUBLICATION_TYPES",
    "DomainClassificationResult",
    "DocumentTypeClassificationResult",
    "PublicationTypeClassificationResult",
    "DocumentUnderstanding",
    "DomainClassifier",
    "DocumentTypeClassifier",
    "PublicationTypeClassifier",
    "classify_document",
]


def classify_document(document: ProcessedDocument) -> DocumentUnderstanding:
    """Runs the full Pass 1 pipeline (see module docstring's diagram) and
    returns one DocumentUnderstanding.

    Overall confidence is the mean of the three stages' own primary-label
    confidences (domain's top score, document_type's top score,
    publication_type's score) — a simple, transparent aggregate rather
    than a re-weighted recombination of all nine-plus individual signal
    scores, consistent with rule #13 (deterministic, explainable, no
    hidden model behind the number).
    """
    domain_result = DomainClassifier().classify(document)
    type_result = DocumentTypeClassifier().classify(document)
    publication_result = PublicationTypeClassifier().classify(document, document_type=type_result.primary_type)

    domain_confidence = dict(domain_result.domains).get(domain_result.primary_domain, 0.0)
    type_confidence = dict(type_result.document_types).get(type_result.primary_type, 0.0)
    overall_confidence = (domain_confidence + type_confidence + publication_result.confidence) / 3

    reasoning = [*domain_result.reasoning, *type_result.reasoning, *publication_result.reasoning]

    matched_features: dict[str, list[str]] = {}
    for stage_features in (
        domain_result.matched_features,
        type_result.matched_features,
        publication_result.matched_features,
    ):
        for label, terms in stage_features.items():
            bucket = matched_features.setdefault(label, [])
            for term in terms:
                if term not in bucket:
                    bucket.append(term)

    return DocumentUnderstanding(
        domain=domain_result.primary_domain,
        domains=domain_result.domains,
        document_type=type_result.primary_type,
        document_types=type_result.document_types,
        publication_type=publication_result.publication_type,
        confidence=overall_confidence,
        reasoning=reasoning,
        matched_features=matched_features,
    )
