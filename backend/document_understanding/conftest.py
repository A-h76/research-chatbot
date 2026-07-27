"""Shared PDF-fixture helper for this package's tests — real PDFs
generated on the fly with PyMuPDF (already a project dependency, see
requirements.txt), no binary fixtures checked into the repo. Mirrors
backend/processing/test_parser.py's own _make_pdf(), centralized here
since several test modules in this package need it.
"""

from pathlib import Path

import fitz
import pytest


def _make_pdf(tmp_path: Path, pages: list[str], metadata: dict | None = None, encrypt: bool = False) -> Path:
    """Writes a real PDF with one page per string in `pages` (each
    inserted as plain text) and returns its path. `encrypt=True` saves it
    password-protected (AES-256) for encrypted-document tests."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        y = 72
        for line in text.splitlines():
            page.insert_text((72, y), line)
            y += 20
    if metadata:
        doc.set_metadata(metadata)

    path = Path(tmp_path) / "sample.pdf"
    if encrypt:
        doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
    else:
        doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def make_pdf(tmp_path):
    def _factory(pages: list[str], metadata: dict | None = None, encrypt: bool = False) -> Path:
        return _make_pdf(tmp_path, pages, metadata, encrypt)

    return _factory
