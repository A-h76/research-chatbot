"""Dataclasses for the document processing pipeline.

ProcessedDocument / DocumentQuality are the package's public output shape
(see package __init__.py docstring for the pipeline they come out of).
The other dataclasses here (ParsedPDF, MetadataExtractionResult,
SectionMatch, SectionExtractionResult) are each pipeline stage's own
richer intermediate result — carrying per-field confidence/reasoning
(rule: "all classifiers must provide explainable reasoning and confidence
scores") that ProcessedDocument/DocumentQuality themselves don't have room
for without changing their given shape. A caller that only wants the
final structured document can ignore them entirely; one building an
admin/debug view of "why did extraction decide this" has them available.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedPDF:
    """PDFParser's output — raw text plus the page-level facts needed by
    QualityAssessor and MetadataExtractor, extracted in one pass so
    neither of those has to re-open or re-parse the file itself.

    Attributes:
        raw_text: Full extracted text, page-boundary sentinels stripped.
        first_page_text: Just page 1's text (sentinels stripped) — where
            title/authors/venue/year/abstract usually live; searching only
            this instead of the whole document avoids false matches from
            later pages (e.g. a reference list entry that looks like a title).
        page_count: Total pages in the PDF, per PyMuPDF — includes pages
            with no extractable text (images, blank pages).
        text_page_count: Pages that yielded non-empty text. page_count >
            text_page_count is the primary signal something didn't extract
            cleanly (most commonly: a scanned/image-only PDF).
        pdf_metadata: The PDF's own embedded metadata dict (title, author,
            subject, ...) from PyMuPDF — empty values where the PDF simply
            doesn't have that field set, never fabricated.
        is_likely_scanned: True when the PDF has pages but essentially no
            extractable text on any of them — the one deterministic OCR-need
            signal this package computes; it does not perform OCR itself
            (see package docstring's Non-Goals).
    """

    raw_text: str
    first_page_text: str
    page_count: int
    text_page_count: int
    pdf_metadata: dict[str, str]
    is_likely_scanned: bool


@dataclass
class MetadataExtractionResult:
    """MetadataExtractor's output. The plain fields feed directly into
    ProcessedDocument; confidence/reasoning are keyed by the same field
    names for anyone that wants to know how sure extraction was."""

    title: str
    authors: list[str]
    venue: str
    year: Optional[int]
    doi: Optional[str]
    abstract: str
    keywords: list[str]
    confidence: dict[str, float] = field(default_factory=dict)
    reasoning: dict[str, str] = field(default_factory=dict)


@dataclass
class SectionMatch:
    """One heading's normalization outcome, in document order — the
    per-heading detail behind SectionExtractionResult's aggregated dicts."""

    raw_heading: str
    normalized_key: Optional[str]
    confidence: float
    reasoning: str


@dataclass
class SectionExtractionResult:
    """SectionExtractor's output. section_order/raw_sections/
    normalized_sections feed ProcessedDocument directly; matches/
    overall_confidence are the explainability detail behind them."""

    section_order: list[str]
    raw_sections: dict[str, str]
    normalized_sections: dict[str, str]
    matches: list[SectionMatch] = field(default_factory=list)
    overall_confidence: float = 0.0


@dataclass
class DocumentQuality:
    """Quality assessment for a processed document.

    Attributes:
        ocr_quality: 0.0-1.0 — confidence the text layer is genuine
            extracted text rather than OCR/scan noise (1.0 = clean digital
            text; low values indicate a likely-scanned or garbled source).
        text_extraction_quality: 0.0-1.0 — how complete/plausible the
            extraction looks (word count relative to page count, etc.),
            independent of whether the source was scanned.
        missing_sections: Normalized section keys expected in a typical
            academic paper but not found (e.g. ["methods", "results"]).
        has_references: Whether a "references"-normalized section was found.
        has_abstract: Whether an "abstract"-normalized section was found.
        has_methods: Whether a "methods"-normalized section was found.
        has_results: Whether a "results"-normalized section was found.
        has_discussion: Whether a "discussion"-normalized section was found.
        confidence: Overall quality confidence, 0.0-1.0.
        warnings: Human-readable, non-fatal issues (e.g. "no methods
            section detected").
        errors: Human-readable, more serious issues (e.g. "no extractable
            text at all").
    """

    ocr_quality: float
    text_extraction_quality: float
    missing_sections: list[str]
    has_references: bool
    has_abstract: bool
    has_methods: bool
    has_results: bool
    has_discussion: bool
    confidence: float
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ProcessedDocument:
    """The pipeline's final structured output for one uploaded document.

    id is caller-supplied (e.g. str(UserFile.id)) rather than generated
    here — this package has no database/upload-pipeline dependency (see
    package docstring), so it has no notion of "the" identity for a
    document beyond what its caller already tracks.
    """

    id: str
    title: str
    authors: list[str]
    venue: str
    year: Optional[int]
    doi: Optional[str]
    journal: Optional[str]
    language: str
    abstract: str
    keywords: list[str]
    references: list[str]
    tables: list[dict]
    figures: list[dict]
    section_order: list[str]
    raw_sections: dict[str, str]
    normalized_sections: dict[str, str]
    full_text: str
    page_count: int
    word_count: int
    char_count: int
    quality: DocumentQuality
    created_at: datetime
