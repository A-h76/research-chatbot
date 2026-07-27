"""PDF parsing — the only stage that reads a file off disk.

Standalone rather than a wrap of backend.processing.parser.PDFParser
(see package docstring's reuse table): that class's _split_pages()
computes each page's start offset, uses it, then discards it — this
package needs each page's (start, end) range kept (ParsedDocument.
page_ranges, the traceability.py hook), and re-deriving that from the
legacy result would mean a second pass over the already-extracted text.
Reuses imports.extract_text() for the actual text pull either way (same
as the legacy parser) rather than re-implementing PyMuPDF page iteration.

Corrupted and encrypted PDFs are deliberately NOT caught here. A
corrupted file makes fitz.open() raise naturally; an encrypted one is
detected via is_encrypted/needs_pass (checked, not inferred from a
raise — fitz reports both without raising, but a bare get_text() call on
a locked doc does raise, with a far less useful message) and reported
via a specific ValueError. Both propagate to pipeline.py's stage-level
_run_stage() wrapper, which is this package's one graceful-degradation
safety net for "can't read this file at all" (see pipeline.py). An
unsupported (non-PDF) format is different: not an error, just an empty,
honestly-tagged result — see parse() below.
"""

import re
from pathlib import Path

import fitz  # PyMuPDF

from imports import extract_text

from .enums import DocumentFormat
from .interfaces import BaseParser
from .models import PageOffset, ParsedDocument

# Matches imports/importers/pdf.py's own "\x00PAGE{n}\x00\n" sentinel
# format exactly — this module is a consumer of that convention, not a
# second definition of it.
_PAGE_SENTINEL_RE = re.compile(r"\x00PAGE(\d+)\x00\n?")

_SUFFIX_FORMATS: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".xml": DocumentFormat.XML,
}


class DocumentParser(BaseParser):
    """Extracts raw text, page offsets, and native metadata from a PDF
    file on disk. Does not perform OCR (see package Non-Goals) — a PDF
    with pages but no extractable text on any of them is flagged via
    ParsedDocument.is_likely_scanned rather than processed further."""

    def parse(self, document_path: Path, mime: str = "", name: str = "") -> ParsedDocument:
        fmt = self._detect_format(document_path)
        if fmt != DocumentFormat.PDF:
            # Structural, not an error: an unsupported format is a fact
            # about the input, reported by returning it in `format` —
            # pipeline.py turns that into a warning, no branch needed here.
            return ParsedDocument(format=fmt)

        page_count, pdf_metadata = self._read_native_metadata(document_path)

        sentinel_text = extract_text(str(document_path), mime or "application/pdf", name or document_path.name)
        raw_text, page_ranges = self._split_pages(sentinel_text)
        text_page_count = len(page_ranges)

        first_page_text = ""
        if page_ranges:
            first_page_text = raw_text[page_ranges[0].start : page_ranges[0].end].strip()

        is_likely_scanned = page_count > 0 and text_page_count == 0

        return ParsedDocument(
            raw_text=raw_text,
            first_page_text=first_page_text,
            page_count=page_count,
            text_page_count=text_page_count,
            page_ranges=page_ranges,
            pdf_metadata=pdf_metadata,
            is_likely_scanned=is_likely_scanned,
            format=fmt,
        )

    @staticmethod
    def _detect_format(document_path: Path) -> DocumentFormat:
        return _SUFFIX_FORMATS.get(document_path.suffix.lower(), DocumentFormat.UNKNOWN)

    @staticmethod
    def _read_native_metadata(document_path: Path) -> tuple[int, dict[str, str]]:
        """Also where encryption is detected (see module docstring) —
        this is the first of parse()'s two fitz opens (extract_text()
        below makes the second, for the actual per-page text pull), so
        checking here means a locked or corrupt PDF never reaches that
        heavier second open at all. Unlike backend.processing's
        equivalent, does NOT catch a corrupted-file exception here —
        that's deliberately left to propagate to pipeline.py's stage-
        level wrapper (see module docstring)."""
        with fitz.open(str(document_path)) as doc:
            if doc.is_encrypted or doc.needs_pass:
                raise ValueError("document is encrypted or password-protected")
            metadata = {k: v for k, v in (doc.metadata or {}).items() if v}
            return doc.page_count, metadata

    @staticmethod
    def _split_pages(sentinel_text: str) -> tuple[str, list[PageOffset]]:
        """Strips every \\x00PAGE{n}\\x00 sentinel, returning the clean
        text plus one PageOffset per sentinel found, each already
        adjusted for every sentinel removed before it — callers can slice
        the returned text directly with no further bookkeeping."""
        starts: list[tuple[int, int]] = []  # (page_number, clean_text_offset)
        clean_parts: list[str] = []
        clean_len = 0
        last_end = 0
        for match in _PAGE_SENTINEL_RE.finditer(sentinel_text):
            clean_parts.append(sentinel_text[last_end : match.start()])
            clean_len += match.start() - last_end
            starts.append((int(match.group(1)), clean_len))
            last_end = match.end()
        clean_parts.append(sentinel_text[last_end:])
        raw_text = "".join(clean_parts)

        page_ranges = [
            PageOffset(
                page_number=page_number,
                start=start,
                end=starts[i + 1][1] if i + 1 < len(starts) else len(raw_text),
            )
            for i, (page_number, start) in enumerate(starts)
        ]
        return raw_text, page_ranges
