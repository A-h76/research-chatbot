"""Importer registry — replaces extract_text()'s old if/elif dispatch
chain with an ordered list of Importers. External contract is unchanged:
extract_text(path, mime, name) still returns a plain string ('' = no
readable text, '[...]' = a bracketed note, or the extracted text), so
every existing call site in server.py works without modification."""

from .importers.pdf import PdfImporter
from .importers.docx import DocxImporter
from .importers.pptx import PptxImporter
from .importers.xlsx import XlsxImporter
from .importers.epub import EpubImporter
from .importers.zip import ZipImporter
from .importers.text import TextImporter
from .importers.legacy_office import LegacyOfficeImporter
from .sniff import sniff_text

# Order matters — mirrors the original if/elif chain's priority exactly
# (e.g. a mismatched extension with a matching mime still resolves the
# same importer it did before). EpubImporter must come before ZipImporter:
# an epub's mimetype ("application/epub+zip") contains "zip", which
# ZipImporter's own matches() checks for — without this ordering every
# .epub would still silently fall into the generic zip handler.
_IMPORTERS = [
    PdfImporter(),
    DocxImporter(),
    PptxImporter(),
    XlsxImporter(),
    EpubImporter(),
    ZipImporter(),
    TextImporter(),
    LegacyOfficeImporter(),
]


def resolve(lower_name: str, mime: str):
    """First matching Importer, or None — None falls through to the
    unknown-extension text sniff, same as the original chain's last line."""
    for importer in _IMPORTERS:
        if importer.matches(lower_name, mime or ""):
            return importer
    return None


def extract_text(path: str, mime: str, name: str) -> str:
    """Extract plain text from (almost) any file. Returns '' when a file
    has no readable text (e.g. a scanned/image PDF), or a bracketed
    '[...]' note when a format is recognised but can't be parsed."""
    lower = (name or path or "").lower()
    mime = mime or ""
    try:
        importer = resolve(lower, mime)
        if importer:
            return importer.extract(path, mime, name)
        return sniff_text(path)  # unknown extension: try as text
    except Exception as e:
        return f"[extraction failed: {e}]"
