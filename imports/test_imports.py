"""Self-check for the Import Engine — no framework, no fixtures.
Run: python -m imports.test_imports
"""

import os
import shutil
import tempfile
import zipfile

from imports import extract_text
from imports.registry import resolve


def _write(path, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def test_text_importer_round_trip():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "notes.md")
        _write(p, "# Hello\nresearch notes")
        assert extract_text(p, "text/markdown", "notes.md") == "# Hello\nresearch notes"
    finally:
        shutil.rmtree(d)


def test_legacy_office_returns_a_note_not_an_error():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "thesis.doc")
        _write(p, "not actually parsed")  # content is irrelevant — .doc is never opened
        result = extract_text(p, "application/msword", "thesis.doc")
        assert result.startswith("[") and result.endswith("]")
        assert "re-save it as .docx" in result
    finally:
        shutil.rmtree(d)


def test_registry_resolves_by_priority():
    # resolve() expects an already-lowercased name (extract_text does the
    # lowercasing).
    assert resolve("paper.pdf", "").__class__.__name__ == "PdfImporter"
    # PDF is checked first by extension-OR-mime in both the original
    # if/elif chain and this registry — a docx-named file with a "pdf"
    # mime is still classified as PDF, a preserved quirk, not a new one.
    assert resolve("report.docx", "application/pdf").__class__.__name__ == "PdfImporter"
    assert resolve("report.docx", "").__class__.__name__ == "DocxImporter"


def test_unknown_extension_falls_through_to_sniff():
    d = tempfile.mkdtemp()
    try:
        text_p = os.path.join(d, "data.xyz")
        _write(text_p, "plain text in a weird extension")
        assert extract_text(text_p, "", "data.xyz") == "plain text in a weird extension"

        binary_p = os.path.join(d, "blob.xyz")
        with open(binary_p, "wb") as f:
            f.write(b"\x00\x01\x02binary\xffdata")
        assert extract_text(binary_p, "", "blob.xyz") == ""
    finally:
        shutil.rmtree(d)


def test_zip_importer_recurses_into_members():
    d = tempfile.mkdtemp()
    try:
        zip_path = os.path.join(d, "archive.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "inside the zip")
            zf.writestr("__MACOSX/junk", "ignored")
        result = extract_text(zip_path, "application/zip", "archive.zip")
        assert "inside the zip" in result
        assert "readme.txt" in result
        assert "junk" not in result
    finally:
        shutil.rmtree(d)


def test_extract_text_never_raises_on_a_broken_pdf():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "corrupt.pdf")
        _write(p, "this is not a real PDF file")
        result = extract_text(p, "application/pdf", "corrupt.pdf")
        assert result.startswith("[extraction failed:")
    finally:
        shutil.rmtree(d)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
