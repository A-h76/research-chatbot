"""Document Processing Engine.

    PDF Upload
        |
        v
    PDFParser            (parser.py)    -- raw text, page count, native metadata
        |
        v
    MetadataExtractor     (metadata.py)  -- title, authors, venue, year, DOI, abstract
        |
        v
    SectionExtractor      (sections.py)  -- heading detection + normalization
        |
        v
    QualityAssessor       (quality.py)   -- OCR/extraction quality, missing sections
        |
        v
    ProcessedDocument     (models.py)    -- structured output

Each stage is an independently usable, dependency-injected class (no
stage imports another stage's caller, no stage reaches into server.py —
see this project's brain.md §3 on constructor injection over `import
server`). process_pdf() below is a thin convenience that chains all four
in the order the diagram shows; nothing requires calling it that way —
a future caller with different needs (e.g. it already has ParsedPDF from
elsewhere) can use the stage classes directly instead.

Non-goals (see the task this package was built under for the full list):
full OCR (PDFParser flags a likely-scanned PDF via
DocumentQuality.ocr_quality/warnings, it does not run OCR itself — that's
a real, separate future capability, not attempted here), ML/LLM-based
extraction (every stage here is deterministic pattern/rule matching, on
purpose — the extension point for a future ML/LLM classifier is
implementing the same stage interface, e.g. a second MetadataExtractor-
shaped class, not a flag inside this one), and image/table extraction
(ProcessedDocument.tables/figures are always empty lists today; populating
them is layout-analysis work this package doesn't do).

Extensibility (no core pipeline logic changes needed for any of these):
  - New section type: add one entry to normalization.NORMALIZED_SECTIONS.
  - New heading pattern: add one branch to sections._detect_heading().
  - New quality signal: add one method to QualityAssessor and fold its
    result into DocumentQuality.confidence/warnings/errors.
  - New metadata field: add it to MetadataExtractionResult/
    ProcessedDocument and one _extract_<field> method to MetadataExtractor.
"""

from datetime import datetime, timezone

from .metadata import MetadataExtractor
from .models import (
    DocumentQuality,
    MetadataExtractionResult,
    ParsedPDF,
    ProcessedDocument,
    SectionExtractionResult,
    SectionMatch,
)
from .normalization import NORMALIZED_SECTIONS, NormalizationMatch, normalize_heading
from .parser import PDFParser
from .quality import QualityAssessor
from .sections import SectionExtractor

__all__ = [
    "PDFParser",
    "MetadataExtractor",
    "SectionExtractor",
    "QualityAssessor",
    "ProcessedDocument",
    "DocumentQuality",
    "ParsedPDF",
    "MetadataExtractionResult",
    "SectionExtractionResult",
    "SectionMatch",
    "NormalizationMatch",
    "NORMALIZED_SECTIONS",
    "normalize_heading",
    "process_pdf",
]


def process_pdf(
    path: str,
    doc_id: str,
    mime: str = "application/pdf",
    name: str = "",
    language: str = "en",
) -> ProcessedDocument:
    """Runs the full pipeline (see module docstring's diagram) and
    returns one ProcessedDocument.

    `doc_id` is caller-supplied (see ProcessedDocument.id's own docstring
    in models.py) — this function has no database dependency and mints
    no identity of its own. `language` is not auto-detected (no language-
    detection dependency exists in this codebase today, and adding one
    wasn't asked for); it's a pass-through default, correct for this
    project's current English-only usage, and is exactly the kind of
    per-field extension point future work could replace without touching
    this function's other logic.
    """
    parsed = PDFParser().parse(path, mime, name)
    sections = SectionExtractor().extract(parsed.raw_text)
    metadata = MetadataExtractor().extract(parsed, sections)
    quality = QualityAssessor().assess(parsed, sections)

    full_text = parsed.raw_text
    words = full_text.split()

    # references.py wasn't in this task's file list — no per-citation
    # parser exists yet, so each non-empty line of the detected
    # "references" section is treated as one reference entry. A real
    # reference *parser* (splitting a single-paragraph reference list,
    # extracting per-citation authors/year/title) is future work, not
    # attempted here.
    references_blob = sections.normalized_sections.get("references", "")
    references = [line.strip() for line in references_blob.splitlines() if line.strip()]

    return ProcessedDocument(
        id=doc_id,
        title=metadata.title,
        authors=metadata.authors,
        venue=metadata.venue,
        year=metadata.year,
        doi=metadata.doi,
        journal=metadata.venue or None,
        language=language,
        abstract=metadata.abstract,
        keywords=metadata.keywords,
        references=references,
        tables=[],
        figures=[],
        section_order=sections.section_order,
        raw_sections=sections.raw_sections,
        normalized_sections=sections.normalized_sections,
        full_text=full_text,
        page_count=parsed.page_count,
        word_count=len(words),
        char_count=len(full_text),
        quality=quality,
        created_at=datetime.now(timezone.utc),
    )
