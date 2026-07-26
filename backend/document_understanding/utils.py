"""Shared helpers: adapters onto backend.processing's already-tested
extractors (see metadata.py/quality.py, which are the only callers of
the two to_legacy_* functions below), plus small offset/text utilities
traceability.py uses to turn a character position into a page/paragraph
number and a readable snippet.

The to_legacy_* adapters are pure field mapping — no re-parsing, no
re-scanning the document — so composing over backend.processing here
costs nothing extra over a second full pass (see parser.py's module
docstring for the one place that tradeoff does NOT hold, which is why
parser.py does not have an adapter here).
"""

from typing import Optional

from backend.processing.models import ParsedPDF, SectionExtractionResult

from .enums import SectionType
from .models import DocumentStructure, PageOffset, ParsedDocument


def to_legacy_parsed(parsed: ParsedDocument) -> ParsedPDF:
    """Maps this package's ParsedDocument onto backend.processing.models.
    ParsedPDF — used to hand data to backend.processing.metadata.
    MetadataExtractor / backend.processing.quality.QualityAssessor
    without duplicating their heuristics here."""
    return ParsedPDF(
        raw_text=parsed.raw_text,
        first_page_text=parsed.first_page_text,
        page_count=parsed.page_count,
        text_page_count=parsed.text_page_count,
        pdf_metadata=dict(parsed.pdf_metadata),
        is_likely_scanned=parsed.is_likely_scanned,
    )


def to_legacy_sections(structure: DocumentStructure) -> SectionExtractionResult:
    """Maps this package's DocumentStructure onto backend.processing.
    models.SectionExtractionResult. `matches` is left empty — the new
    DocumentStructure doesn't retain per-heading SectionMatch records
    (only the aggregate `confidence`), and neither
    backend.processing.metadata.MetadataExtractor nor
    backend.processing.quality.QualityAssessor read that field, only
    `normalized_sections`."""
    return SectionExtractionResult(
        section_order=list(structure.heading_order),
        raw_sections=dict(structure.raw_headings),
        normalized_sections={
            section_type.value: content
            for section_type, content in structure.normalized_headings.items()
            if section_type != SectionType.OTHER
        },
        matches=[],
        overall_confidence=structure.confidence,
    )


def page_at_offset(page_ranges: list[PageOffset], offset: int) -> Optional[int]:
    """The 1-based page number whose [start, end) range contains
    `offset`, or None if it falls outside every known range (e.g. the
    document had no text-bearing pages at all)."""
    for page_range in page_ranges:
        if page_range.start <= offset < page_range.end:
            return page_range.page_number
    return None


def paragraph_index_at(text: str, offset: int) -> int:
    """0-based index of the "\\n\\n"-delimited paragraph containing
    `offset` — a simple, deterministic paragraph-boundary heuristic
    (blank-line-separated blocks), not real layout analysis."""
    return text.count("\n\n", 0, offset)


def snippet_at(text: str, start: int, end: int, context: int = 60) -> str:
    """A short excerpt around [start, end), for EvidenceReference.
    text_snippet — enough surrounding context to be recognizable without
    reproducing the whole matched span verbatim when it's long."""
    snippet_start = max(0, start - context)
    snippet_end = min(len(text), end + context)
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""
    return f"{prefix}{text[snippet_start:snippet_end]}{suffix}"
