"""PDF text extraction.

Reuses imports.extract_text() (imports/importers/pdf.py's PdfImporter)
for the actual text extraction rather than re-implementing it — that
importer already handles PyMuPDF's quirks and already embeds per-page
sentinels this module also happens to need (see _PAGE_SENTINEL_RE below).
Page count / native PDF metadata come from a second, direct PyMuPDF open,
since imports.extract_text()'s contract is deliberately "returns plain
text" only (imports/interface.py) — nothing here duplicates its
extraction logic, it just reads the two extra facts that contract
doesn't expose.
"""

import re

from imports import extract_text

from .models import ParsedPDF

# Matches imports/importers/pdf.py's own "\x00PAGE{n}\x00\n" sentinel
# format exactly — this module is a consumer of that convention, not a
# second definition of it; if the importer's sentinel format ever changes,
# this is the one other place that needs to change with it.
_PAGE_SENTINEL_RE = re.compile(r"\x00PAGE(\d+)\x00\n?")


class PDFParser:
    """Extracts raw text, page count, and native PDF metadata from a PDF
    file on disk. Does not perform OCR (see package Non-Goals) — a PDF
    with no extractable text on any page is flagged via
    ParsedPDF.is_likely_scanned rather than processed further here."""

    def parse(self, path: str, mime: str = "application/pdf", name: str = "") -> ParsedPDF:
        """Parses the PDF at `path`. `mime`/`name` are forwarded to
        imports.extract_text() for format dispatch (matching every other
        caller of that function elsewhere in this codebase) — `name`
        should be the original filename, not `path`, when they differ
        (e.g. a temp file path with no meaningful extension)."""
        sentinel_text = extract_text(path, mime, name or path)
        raw_text, page_positions = self._split_pages(sentinel_text)

        page_count, pdf_metadata = self._read_native_metadata(path)
        text_page_count = len(page_positions)

        first_page_text = ""
        if page_positions:
            first_start = page_positions[0][1]
            second_start = page_positions[1][1] if len(page_positions) > 1 else len(raw_text)
            first_page_text = raw_text[first_start:second_start].strip()

        is_likely_scanned = page_count > 0 and text_page_count == 0

        return ParsedPDF(
            raw_text=raw_text,
            first_page_text=first_page_text,
            page_count=page_count,
            text_page_count=text_page_count,
            pdf_metadata=pdf_metadata,
            is_likely_scanned=is_likely_scanned,
        )

    @staticmethod
    def _split_pages(sentinel_text: str) -> tuple[str, list[tuple[int, int]]]:
        """Strips every \\x00PAGE{n}\\x00 sentinel, returning the clean
        text plus [(page_number, clean_text_offset), ...] for each
        sentinel that was found — the offsets are into the *returned*
        clean text, already adjusted for every sentinel removed before it,
        so callers can slice `clean_text` directly without redoing that
        bookkeeping themselves."""
        positions: list[tuple[int, int]] = []
        clean_parts: list[str] = []
        clean_len = 0
        last_end = 0
        for match in _PAGE_SENTINEL_RE.finditer(sentinel_text):
            clean_parts.append(sentinel_text[last_end : match.start()])
            clean_len += match.start() - last_end
            positions.append((int(match.group(1)), clean_len))
            last_end = match.end()
        clean_parts.append(sentinel_text[last_end:])
        return "".join(clean_parts), positions

    @staticmethod
    def _read_native_metadata(path: str) -> tuple[int, dict[str, str]]:
        """Best-effort: a PDF that PyMuPDF can't even open for metadata
        (corrupt file, etc.) yields page_count=0 and no metadata rather
        than raising — imports.extract_text() already handles the "can't
        read this file" case for the text-extraction half of this class;
        this mirrors that same fail-soft behavior for the metadata half."""
        try:
            import fitz

            with fitz.open(path) as doc:
                metadata = {k: v for k, v in (doc.metadata or {}).items() if v}
                return doc.page_count, metadata
        except Exception:
            return 0, {}
