"""Behavioral contracts for Pass 2's four detectors.

DocumentClassificationPipeline (pipeline.py) depends only on these,
constructor-injected, never on a concrete detector class directly — a
future ML/LLM-backed detector is a new class implementing the matching
interface, nothing in pipeline.py changes for that to slot in.

No BaseKeywordExtractor/BaseConfidenceEngine/BaseReasoningBuilder: those
are plain functions (keywords.py/confidence.py/reasoning.py), not
detectors — there's no plausible second implementation of "score these
matched signals" to swap in behind an interface, same reasoning
backend.document_understanding.interfaces gives for not having a
BaseStatisticsCalculator.
"""

from abc import ABC, abstractmethod

from backend.document_understanding.models import ProcessedDocument

from .models import ClassificationDecision


class BaseDocumentTypeDetector(ABC):
    """Classifies a document's type (research article, case report,
    systematic review, ...). See document_type.py's DocumentTypeDetector."""

    @abstractmethod
    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        raise NotImplementedError


class BaseDomainDetector(ABC):
    """Classifies a document's scientific domain. See domain.py's
    DomainDetector."""

    @abstractmethod
    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        raise NotImplementedError


class BaseStudyDesignDetector(ABC):
    """Classifies a document's study design (RCT, cohort, benchmark, ...).
    See study_design.py's StudyDesignDetector."""

    @abstractmethod
    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        raise NotImplementedError


class BaseReportingGuidelineDetector(ABC):
    """Classifies which reporting guideline (if any) a document follows.
    See reporting_guideline.py's ReportingGuidelineDetector.

    Implementations may accept an additional optional `study_design`
    keyword beyond this signature (a document already classified as an
    RCT strongly corroborates CONSORT, for instance — the same "use an
    already-classified label as extra corroborating evidence" pattern
    backend.classification.pass1.publication.PublicationTypeClassifier
    uses with document_type) — pipeline.py, which runs study_design
    detection first, passes it; a standalone caller using just this
    interface still gets a correct, if weaker-signal, classification."""

    @abstractmethod
    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        raise NotImplementedError
