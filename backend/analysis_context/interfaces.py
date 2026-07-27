"""Behavioral contracts for the Analysis Context Engine's five profilers.

AnalysisContextPipeline (pipeline.py) depends only on these, constructor-
injected, never on a concrete profiler class directly. Each profiler
takes only (document, classification) and derives everything it needs
from those two already-fully-populated objects — no profiler consumes
another profiler's output (matching backend.classification.pass2's own
"Detector Independence... no shared state" principle, one level up the
pipeline): document_type/domain/study_design/reporting_guideline already
live on `classification`, and section presence/completeness already
lives on `document.structure`, so nothing here needs a sibling profile
as an extra input the way pass2's ReportingGuidelineDetector needed
study_design/document_type (those were products of sibling *detectors*,
not already present in pass2's own raw input).

No BaseConfidenceEngine/BaseQualityProfiler: confidence.py's aggregation
and quality_profile.py's reliability scoring are each plain, single-
implementation arithmetic over already-computed profile/quality data —
same "no interface with one implementation and no foreseeable second"
reasoning backend.document_understanding.interfaces and backend.
classification.pass2.interfaces both already give for their own
non-interfaced helpers.
"""

from abc import ABC, abstractmethod

from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .models import AnalysisProfile, DocumentProfile, PromptProfile, RoutingProfile, SectionProfile


class BaseDocumentProfiler(ABC):
    """Profiles document type/domain/study_design/audience/complexity.
    See document_profile.py's DocumentProfiler."""

    @abstractmethod
    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> DocumentProfile:
        raise NotImplementedError


class BaseSectionProfiler(ABC):
    """Assesses section presence/completeness. See section_profile.py's
    SectionProfiler."""

    @abstractmethod
    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> SectionProfile:
        raise NotImplementedError


class BaseAnalysisProfiler(ABC):
    """Determines which analyses are supported and whether the document
    is ready for them. See analysis_profile.py's AnalysisProfiler."""

    @abstractmethod
    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> AnalysisProfile:
        raise NotImplementedError


class BaseRoutingProfiler(ABC):
    """Decides which downstream module pipeline this document should be
    routed through. See routing_profile.py's RoutingProfiler."""

    @abstractmethod
    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> RoutingProfile:
        raise NotImplementedError


class BasePromptProfiler(ABC):
    """Determines prompt family/strategy/section priorities. See
    prompt_profile.py's PromptProfiler."""

    @abstractmethod
    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> PromptProfile:
        raise NotImplementedError
