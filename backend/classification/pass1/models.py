"""Dataclasses and canonical label lists for Pass 1 classification.

DOMAINS / DOCUMENT_TYPES / PUBLICATION_TYPES are the closed label sets
each classifier scores candidates against — adding a new label to one of
these tuples (plus a matching entry in keywords.py) is the whole change
needed to recognize it; nothing in domain.py/type.py/publication.py
hardcodes a label name (see each classifier's own docstring on this).

DocumentUnderstanding is Pass 1's public output shape, given verbatim by
the task this package was built under. The three *ClassificationResult
dataclasses are each classifier's own richer intermediate result — same
"structured result carries reasoning/confidence, final dataclass stays
exactly as specified" split backend/processing/models.py already uses
for the same reason (rule: "all classifiers must provide explainable
reasoning and confidence scores").
"""

from dataclasses import dataclass, field

# Closed label sets. Extensibility means: add a label here, add its
# keywords/venues to keywords.py, done — no classifier logic changes.
DOMAINS: tuple[str, ...] = (
    "medical",  # Medicine, Dentistry, Nursing, Pharmacy, Allied Health
    "computer_science",  # AI, ML, Algorithms, Systems, Theory
    "physics",  # Physics, Astronomy, Quantum
    "economics",  # Economics, Finance, Business
    "law",  # Law, Legal Studies
    "education",  # Education, Pedagogy
    "engineering",  # Engineering, Robotics, Electrical, Mechanical
    "biology",  # Biology, Genetics, Ecology
    "chemistry",  # Chemistry, Biochemistry
    "psychology",  # Psychology, Behavioral Science
    "social_sciences",  # Sociology, Political Science, Anthropology
    "other",
)

DOCUMENT_TYPES: tuple[str, ...] = (
    "research_article",
    "clinical_guideline",
    "review",
    "case_report",
    "protocol",
    "dataset_paper",
    "white_paper",
    "position_paper",
    "conference_paper",
    "thesis",
    "preprint",
    "report",
    "editorial",
    "other",
)

PUBLICATION_TYPES: tuple[str, ...] = (
    "journal_article",
    "conference_paper",
    "thesis",
    "preprint",
    "report",
    "white_paper",
    "book_chapter",
    "other",
)


@dataclass
class DomainClassificationResult:
    """DomainClassifier's output. `domains` is every candidate that
    matched at least one signal, ranked descending by confidence —
    `primary_domain` is just `domains[0][0]` (or "other" if empty),
    kept as its own field so callers don't have to re-derive it."""

    primary_domain: str
    domains: list[tuple[str, float]]
    reasoning: list[str]
    matched_features: dict[str, list[str]]


@dataclass
class DocumentTypeClassificationResult:
    """DocumentTypeClassifier's output — same shape as
    DomainClassificationResult, for the document_type label set instead."""

    primary_type: str
    document_types: list[tuple[str, float]]
    reasoning: list[str]
    matched_features: dict[str, list[str]]


@dataclass
class PublicationTypeClassificationResult:
    """PublicationTypeClassifier's output. Only one label (not a ranked
    list) — DocumentUnderstanding.publication_type is a single str with no
    matching ...s plural field, so this mirrors that rather than adding
    ranked alternatives the final shape has nowhere to put."""

    publication_type: str
    confidence: float
    reasoning: list[str]
    matched_features: dict[str, list[str]]


@dataclass
class DocumentUnderstanding:
    """Pass 1's final structured output for one ProcessedDocument.

    Attributes:
        domain: Primary domain (DOMAINS member, "other" if nothing matched).
        domains: Every domain that matched at least one signal, as
            (domain, confidence) pairs, descending by confidence.
        document_type: Primary document type (DOCUMENT_TYPES member).
        document_types: Every document type that matched at least one
            signal, as (type, confidence) pairs, descending by confidence.
        publication_type: Single best publication type (PUBLICATION_TYPES
            member).
        confidence: Overall Pass 1 confidence — the mean of the three
            stages' own primary-label confidences.
        reasoning: Every stage's reasoning strings, concatenated in
            pipeline order (domain, then document_type, then
            publication_type) — a flat audit trail, not nested per-stage,
            since nothing downstream needs to know which stage said what.
        matched_features: Every stage's matched_features dicts, merged
            (a label appearing in more than one stage's output, e.g.
            "medical" as both a domain and coincidentally a document-type
            keyword bucket, keeps both stages' evidence concatenated).
    """

    domain: str
    domains: list[tuple[str, float]]
    document_type: str
    document_types: list[tuple[str, float]]
    publication_type: str
    confidence: float
    reasoning: list[str] = field(default_factory=list)
    matched_features: dict[str, list[str]] = field(default_factory=dict)
