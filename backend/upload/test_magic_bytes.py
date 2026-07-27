"""Unit tests for magic-byte sniffing (PR3)."""

import io
import zipfile

import pytest

from backend.upload.magic_bytes import sniff_kind, validate_magic_bytes
from backend.upload.validation import ValidationError, validate_upload_bytes


def _minimal_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        zf.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


def _minimal_epub() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", "<container/>")
    return buf.getvalue()


def _minimal_pptx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        zf.writestr("ppt/presentation.xml", "<p:presentation/>")
    return buf.getvalue()


def test_pdf_magic_ok():
    mime = validate_magic_bytes(b"%PDF-1.4\n%", ".pdf")
    assert mime == "application/pdf"


def test_pdf_extension_with_png_bytes_rejected():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    with pytest.raises(ValidationError) as exc:
        validate_magic_bytes(png, ".pdf")
    assert exc.value.code == "invalid_mime"


def test_txt_ok_and_rejects_binary():
    assert validate_magic_bytes(b"hello world\n", ".txt") == "text/plain"
    with pytest.raises(ValidationError):
        validate_magic_bytes(b"%PDF-1.4", ".txt")


def test_docx_and_epub_zip_structure():
    assert "wordprocessingml" in validate_magic_bytes(_minimal_docx(), ".docx")
    assert validate_magic_bytes(_minimal_epub(), ".epub") == "application/epub+zip"
    assert "presentationml" in validate_magic_bytes(_minimal_pptx(), ".pptx")


def test_docx_extension_on_epub_bytes_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_magic_bytes(_minimal_epub(), ".docx")
    assert exc.value.code == "invalid_mime"


def test_jpeg_and_png():
    assert sniff_kind(b"\xff\xd8\xff\xe0" + b"\x00" * 8) == "jpeg"
    assert sniff_kind(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == "png"


def test_validate_upload_bytes_end_to_end(monkeypatch):
    monkeypatch.delenv("CLAMAV_ENABLED", raising=False)
    ext, mime = validate_upload_bytes(b"%PDF-1.7\n", "paper.pdf")
    assert ext == ".pdf"
    assert mime == "application/pdf"
