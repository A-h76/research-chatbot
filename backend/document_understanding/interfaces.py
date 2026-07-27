"""Behavioral contracts for every major pipeline component.

Each concrete implementation in this package (parser.py's DocumentParser,
language.py's StopwordLanguageDetector, ...) implements exactly one of
these — DocumentUnderstandingPipeline (pipeline.py) depends only on these
interfaces, constructor-injected, never on a concrete class directly (no
component instantiates another component itself). A future DOCX/XML/
HTML/OCR parser, or a future ML/LLM-backed extractor, is a new class
implementing the matching interface below — nothing in pipeline.py or
any other stage needs to change for that to slot in.

No BaseStatisticsCalculator: statistics.py's StatisticsCalculator is pure
arithmetic aggregation over already-extracted data, with no plausible
second implementation ever swapping in behind an interface — an ABC with
exactly one implementation and no foreseeable second one is exactly the
unnecessary abstraction this package's own design rules say to avoid.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .enums import DocumentLanguage
from .models import (
    DocumentMetadata,
    DocumentQuality,
    DocumentStatistics,
    DocumentStructure,
    EvidenceReference,
    HeadingCandidate,
    LanguageDetectionResult,
    NormalizedHeading,
    ParsedDocument,
)


class BaseParser(ABC):
    """Extracts raw text and structural facts (page count/offsets, native
    metadata) from a document file. See parser.py's DocumentParser (the
    only implementation today — PDF)."""

    @abstractmethod
    def parse(self, document_path: Path, mime: str = "", name: str = "") -> ParsedDocument:
        """`mime`/`name` are optional hints (matching this codebase's
        existing imports.extract_text() convention) — implementations
        that don't need them may ignore them."""
        raise NotImplementedError


class BaseLanguageDetector(ABC):
    """Detects a document's primary language from its text. See
    language.py's StopwordLanguageDetector."""

    @abstractmethod
    def detect(self, text: str) -> LanguageDetectionResult:
        raise NotImplementedError


class BaseHeadingDetector(ABC):
    """Finds heading-shaped lines in plain text, without judging what
    section (if any) each one represents — that's BaseHeadingNormalizer's
    job. See headings.py's HeadingDetector."""

    @abstractmethod
    def detect(self, text: str) -> list[HeadingCandidate]:
        raise NotImplementedError


class BaseHeadingNormalizer(ABC):
    """Maps one raw heading's text to a canonical SectionType. See
    normalization.py's HeadingNormalizer."""

    @abstractmethod
    def normalize(self, raw_heading: str) -> NormalizedHeading:
        raise NotImplementedError


class BaseSectionBuilder(ABC):
    """Combines heading detection + normalization into a full
    DocumentStructure. Implementations take their BaseHeadingDetector/
    BaseHeadingNormalizer via constructor injection, not as build()
    arguments — build() only takes the data it operates on. See
    sections.py's SectionBuilder."""

    @abstractmethod
    def build(self, text: str) -> DocumentStructure:
        raise NotImplementedError


class BaseMetadataExtractor(ABC):
    """Extracts bibliographic metadata. See metadata.py's
    MetadataExtractor."""

    @abstractmethod
    def extract(
        self,
        parsed: ParsedDocument,
        structure: Optional[DocumentStructure],
        language: DocumentLanguage,
    ) -> DocumentMetadata:
        """`structure`, if already built (per the pipeline order), lets
        the abstract come from DocumentStructure's own detected
        "abstract" section rather than a weaker fallback heuristic —
        optional, this must still work standalone without it."""
        raise NotImplementedError


class BaseQualityAssessor(ABC):
    """Assesses extraction/structural quality. See quality.py's
    QualityAssessor."""

    @abstractmethod
    def assess(
        self,
        parsed: ParsedDocument,
        metadata: DocumentMetadata,
        structure: DocumentStructure,
        statistics: DocumentStatistics,
    ) -> DocumentQuality:
        raise NotImplementedError


class BaseTraceabilityBuilder(ABC):
    """Maps extracted facts back to their source location. See
    traceability.py's TraceabilityBuilder."""

    @abstractmethod
    def build(
        self,
        parsed: ParsedDocument,
        metadata: DocumentMetadata,
        structure: DocumentStructure,
    ) -> dict[str, EvidenceReference]:
        raise NotImplementedError
