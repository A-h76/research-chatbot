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


def _write_minimal_epub(path, chapters):
    """chapters: [(id, filename, xhtml_body_text), ...] in spine order."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?>'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        manifest_items = "".join(
            f'<item id="{cid}" href="{fname}" media-type="application/xhtml+xml"/>' for cid, fname, _ in chapters
        )
        spine_items = "".join(f'<itemref idref="{cid}"/>' for cid, _, _ in chapters)
        zf.writestr(
            "OEBPS/content.opf",
            '<?xml version="1.0"?>'
            '<package xmlns="http://www.idpf.org/2007/opf">'
            f"<manifest>{manifest_items}</manifest>"
            f"<spine>{spine_items}</spine>"
            "</package>",
        )
        for _, fname, body in chapters:
            zf.writestr(
                f"OEBPS/{fname}",
                '<?xml version="1.0"?>'
                '<html xmlns="http://www.w3.org/1999/xhtml"><head><style>.x{}</style></head>'
                f"<body><p>{body}</p><script>ignored();</script></body></html>",
            )


def test_epub_importer_extracts_spine_text_in_order():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "book.epub")
        _write_minimal_epub(
            p,
            [
                ("ch1", "ch1.xhtml", "Chapter one text"),
                ("ch2", "ch2.xhtml", "Chapter two text"),
            ],
        )
        result = extract_text(p, "application/epub+zip", "book.epub")
        assert "Chapter one text" in result
        assert "Chapter two text" in result
        assert result.index("Chapter one text") < result.index("Chapter two text")
        assert "ignored" not in result  # <script> content excluded
    finally:
        shutil.rmtree(d)


def test_epub_importer_takes_priority_over_zip_importer():
    # application/epub+zip contains "zip" — ZipImporter's own matches()
    # would also accept it; registry order must still pick EpubImporter.
    assert resolve("book.epub", "application/epub+zip").__class__.__name__ == "EpubImporter"


def test_epub_importer_handles_corrupt_archive():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "corrupt.epub")
        _write(p, "not actually a zip file")
        result = extract_text(p, "application/epub+zip", "corrupt.epub")
        assert result.startswith("[extraction failed:")
    finally:
        shutil.rmtree(d)


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
