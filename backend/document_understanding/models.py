"""Dataclasses for the Document Understanding Engine.

ProcessedDocument is a lightweight container composing five focused
sub-models (DocumentMetadata, DocumentStructure, DocumentStatistics,
DocumentQuality, plus the traceability dict of EvidenceReference) rather
than one flat dataclass with every field inline — this is the explicit
design requirement this package was built under ("this architecture must
remain stable even if hundreds of new metadata fields are added later"):
a new field goes on exactly one focused sub-model, never risks colliding
with an unrelated one, and nothing needs touching outside that one model
plus the one extractor that populates it.

The remaining dataclasses here (ParsedDocument, PageOffset,
LanguageDetectionResult, HeadingCandidate, NormalizedHeading, StageLog)
are inter-stage data, not part of ProcessedDocument's own public shape —
each is documented under the pipeline stage that produces it.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import DocumentFormat, DocumentLanguage, ExtractionStatus, HeadingType, QualityLevel, SectionType

# ------------------------------------------------------------ parser.py's output


@dataclass(frozen=True)
class PageOffset:
    """One page's character range within ParsedDocument.raw_text —
    [start, end), i.e. `raw_text[start:end]` is that page's own text.
    This is the one fact backend.processing's equivalent (ParsedPDF)
    computes and then discards (see parser.py's module docstring) —
    keeping it is what makes real page-level EvidenceReferences possible
    without a second pass over the document."""

    page_number: int
    start: int
    end: int


@dataclass
class ParsedDocument:
    """DocumentParser's output — see parser.py.

    Attributes:
        raw_text: Full extracted text, page-boundary sentinels stripped.
        first_page_text: Just page 1's text — where title/authors/venue/
            year/abstract usually live.
        page_count: Total pages, per PyMuPDF — includes pages with no
            extractable text (images, blank pages).
        text_page_count: Pages that yielded non-empty text.
        page_ranges: Every text-bearing page's PageOffset, in page order —
            the traceability.py hook (see that module).
        pdf_metadata: The PDF's own embedded metadata dict, never fabricated.
        is_likely_scanned: True when the PDF has pages but essentially no
            extractable text on any of them.
        format: Detected input format — PDF today; other members exist so
            an unsupported format degrades to a clear warning rather than
            a generic failure (see parser.py).
    """

    raw_text: str = ""
    first_page_text: str = ""
    page_count: int = 0
    text_page_count: int = 0
    page_ranges: list[PageOffset] = field(default_factory=list)
    pdf_metadata: dict[str, str] = field(default_factory=dict)
    is_likely_scanned: bool = False
    format: DocumentFormat = DocumentFormat.UNKNOWN


# ------------------------------------------------------------ language.py's output


@dataclass
class LanguageDetectionResult:
    """StopwordLanguageDetector's output — see language.py."""

    language: DocumentLanguage
    confidence: float
    reasoning: str


# ------------------------------------------------------------ headings.py / normalization.py output


@dataclass
class HeadingCandidate:
    """One line (or line pair, for underline-style) HeadingDetector
    decided looks like a heading — see headings.py. Offsets are into
    whatever text string was passed to detect(), not yet normalized."""

    raw_heading: str
    heading_type: HeadingType
    start_offset: int
    end_offset: int  # end of the heading line itself, not its section's content


@dataclass
class NormalizedHeading:
    """HeadingNormalizer's output for one raw heading — see
    normalization.py. Thin wrapper around backend.processing.
    normalization.normalize_heading()'s own NormalizationMatch, with the
    string key upgraded to a SectionType member."""

    section_type: SectionType
    confidence: float
    reasoning: str


# ------------------------------------------------------------ ProcessedDocument's 5 sub-models


@dataclass
class DocumentMetadata:
    """Bibliographic metadata."""

    title: str = ""
    subtitle: Optional[str] = None

    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    corresponding_author: Optional[str] = None

    venue: str = ""
    journal: Optional[str] = None
    conference: Optional[str] = None

    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    arxiv_id: Optional[str] = None
    clinical_trials_id: Optional[str] = None

    publication_year: Optional[int] = None
    publication_type: Optional[str] = None

    keywords: list[str] = field(default_factory=list)
    abstract: str = ""

    language: DocumentLanguage = DocumentLanguage.UNKNOWN
    license: Optional[str] = None

    raw_metadata: dict[str, str] = field(default_factory=dict)

    confidence: dict[str, float] = field(default_factory=dict)
    reasoning: dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentStructure:
    """Section/heading structure. normalized_headings is enum-keyed
    (SectionType), unlike backend.processing's string-keyed equivalent —
    see sections.py.

    section_offsets backs traceability.py: for each *raw* heading (the
    same keys as raw_headings), the (start, end) character range of that
    section's *content* (not the heading line itself) within
    ProcessedDocument.full_text.

    heading_types (same keys again) backs quality.py's layout_quality —
    the one piece of HeadingCandidate data that would otherwise be lost
    once headings.py's output is folded into this class.

    section_types (same keys again) is the reverse of normalized_headings
    — which SectionType each raw heading normalized to — so
    traceability.py can locate a normalized section's source heading
    without re-running normalization.
    """

    heading_order: list[str] = field(default_factory=list)
    raw_headings: dict[str, str] = field(default_factory=dict)
    normalized_headings: dict[SectionType, str] = field(default_factory=dict)
    section_offsets: dict[str, tuple[int, int]] = field(default_factory=dict)
    heading_types: dict[str, HeadingType] = field(default_factory=dict)
    section_types: dict[str, SectionType] = field(default_factory=dict)
    appendix: Optional[str] = None
    references: list[str] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    figures: list[dict] = field(default_factory=list)
    supplementary_material: Optional[str] = None
    confidence: float = 0.0


@dataclass
class DocumentStatistics:
    """Pure counts/derived numbers over the parsed+structured document —
    see statistics.py. No confidence/reasoning here: every field is exact
    arithmetic over already-extracted data, not a heuristic guess."""

    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    estimated_reading_time_minutes: float = 0.0
    reference_count: int = 0
    figure_count: int = 0
    table_count: int = 0
    heading_count: int = 0
    section_count: int = 0


@dataclass
class DocumentQuality:
    """Multi-dimensional quality assessment — see quality.py.

    Attributes:
        ocr_quality: 0.0-1.0, reused verbatim from backend.processing's
            equivalent — confidence the text layer is genuine extracted
            text rather than scan/OCR noise.
        extraction_quality: 0.0-1.0, reused verbatim (renamed from
            backend.processing's text_extraction_quality) — how complete
            the extraction looks relative to page count.
        metadata_quality: 0.0-1.0 — weighted fraction of DocumentMetadata
            fields actually populated.
        section_quality: 0.0-1.0 — blends DocumentStructure.confidence
            with how many of the core academic sections were found.
        layout_quality: 0.0-1.0 — fraction of detected headings matched
            via a strong structural pattern (markdown/numbered/underline)
            rather than the weaker bare-line heuristic; a coarse proxy
            for "does this document have real, parseable structure", not
            genuine layout/DOM analysis.
        completeness: 0.0-1.0 — blended structural + metadata coverage.
        confidence: Overall — weighted mean of the five dimensions above.
        warnings: Human-readable, non-fatal issues.
        errors: Human-readable, more serious issues (e.g. no extractable
            text at all).
    """

    ocr_quality: float = 0.0
    extraction_quality: float = 0.0
    metadata_quality: float = 0.0
    section_quality: float = 0.0
    layout_quality: float = 0.0
    completeness: float = 0.0
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def level(self) -> QualityLevel:
        """Derived, not stored — a stored field could drift out of sync
        with `confidence` if only one of the two were ever updated;
        computing it on read makes that impossible."""
        return QualityLevel.from_score(self.confidence)


@dataclass
class EvidenceReference:
    """Points one extracted fact back to where it came from in the
    source document — see traceability.py.

    confidence here is about *locatability*, not about the fact's own
    correctness (DocumentMetadata.confidence/reasoning already covers
    that): 1.0 means the fact's exact text was found at character_range
    in the document body; ~0.3 means the fact is real (e.g. a title
    pulled from the PDF's own native metadata) but wasn't found verbatim
    in the body text, so page/paragraph/character_range are all None and
    only text_snippet (the fact's own value) is available; 0.0 means the
    fact itself was empty — there is nothing to point to.
    """

    page: Optional[int]
    section: Optional[SectionType]
    paragraph: Optional[int]
    character_range: Optional[tuple[int, int]]
    text_snippet: str
    confidence: float


# ------------------------------------------------------------ pipeline.py's per-stage log


@dataclass
class StageLog:
    """One pipeline stage's execution record — see pipeline.py's
    _run_stage(). Attached to ProcessedDocument.stage_logs so callers
    (including tests) can assert on structured log data directly, in
    addition to it being emitted through stdlib logging."""

    stage: str
    document_id: str
    duration_ms: float
    status: ExtractionStatus
    confidence: Optional[float]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ------------------------------------------------------------ the top-level container


@dataclass
class ProcessedDocument:
    """The pipeline's final structured output for one document —
    composes the five focused sub-models above rather than duplicating
    their fields (see module docstring).

    id is caller-supplied via DocumentUnderstandingPipeline.process()'s
    `metadata` dict (key "id"), or minted fresh with uuid4() if absent —
    this package has no database dependency and no notion of "the"
    identity for a document beyond what its caller tracks.

    schema_version tracks this dataclass's own shape (bump on field
    additions/removals); pipeline_version tracks the extraction logic's
    behavior (bump when a heuristic/regex changes even if the shape is
    stable) — both exist so a stored/cached ProcessedDocument can be
    recognized as needing reprocessing after either kind of change,
    without conflating the two reasons.

    page_ranges is parser.py's ParsedDocument.page_ranges, carried
    through to this final output — added after the fact (a later phase,
    backend.medical_understanding, needed to compute a page number for
    evidence it discovers at a character offset Phase 1.1 itself never
    built a traceability entry for; the transient ParsedDocument this
    came from is otherwise discarded once process() returns). Purely
    additive: defaults to empty, and every field before it is
    unaffected, so no existing keyword-constructed ProcessedDocument
    anywhere in the codebase needed to change.
    """

    id: str
    metadata: DocumentMetadata
    structure: DocumentStructure
    statistics: DocumentStatistics
    quality: DocumentQuality
    traceability: dict[str, EvidenceReference]
    full_text: str
    schema_version: str
    pipeline_version: str
    processing_time_ms: float
    created_at: datetime
    stage_logs: list[StageLog] = field(default_factory=list)
    page_ranges: list[PageOffset] = field(default_factory=list)
