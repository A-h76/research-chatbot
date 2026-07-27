"""Magic-byte content sniffing for uploads (PR3).

Hand-rolled signatures (no libmagic) so Windows/Linux/macOS behave the
same without a native dependency. ZIP-based formats (docx/pptx/xlsx/epub)
are verified via zip member layout after the PK header matches.
"""

from __future__ import annotations

import io
import zipfile
from typing import Optional

from .errors import ValidationError

# How many leading bytes we read for signature checks.
SNIFF_BYTES = 16_384

# Extension → canonical MIME we store (never trust the client header).
CANONICAL_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".epub": "application/epub+zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _startswith(data: bytes, magic: bytes) -> bool:
    return data[: len(magic)] == magic


def sniff_kind(data: bytes) -> Optional[str]:
    """Return a coarse content family label, or None if unrecognized."""
    if not data:
        return None
    if _startswith(data, b"%PDF"):
        return "pdf"
    if _startswith(data, b"\x89PNG\r\n\x1a\n"):
        return "png"
    if _startswith(data, b"\xff\xd8\xff"):
        return "jpeg"
    if _startswith(data, b"GIF87a") or _startswith(data, b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if _startswith(data, b"PK\x03\x04") or _startswith(data, b"PK\x05\x06") or _startswith(data, b"PK\x07\x08"):
        return "zip"
    # OLE Compound File (legacy .doc/.xls/.ppt) — not in allowlist; detect to reject.
    if _startswith(data, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"
    if _looks_like_text(data):
        return "text"
    return "unknown"


def _looks_like_text(data: bytes) -> bool:
    sample = data[:SNIFF_BYTES]
    if b"\x00" in sample:
        return False
    # Allow UTF-8 BOM
    if sample.startswith(b"\xef\xbb\xbf"):
        sample = sample[3:]
    if not sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
        except UnicodeDecodeError:
            return False
    # Reject if too many non-printable control chars (except tab/newline/CR).
    ctrl = sum(1 for b in sample if b < 9 or (13 < b < 32) or b == 127)
    return (ctrl / max(len(sample), 1)) < 0.05


def _zip_names(data: bytes) -> set[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return {i.filename.replace("\\", "/") for i in zf.infolist()}
    except zipfile.BadZipFile as exc:
        raise ValidationError("invalid_mime", "File is not a valid ZIP/Office/EPUB archive") from exc


def _zip_matches_ext(data: bytes, ext: str) -> bool:
    names = _zip_names(data)
    if ext == ".docx":
        return any(n.startswith("word/") for n in names) and any(
            n == "[Content_Types].xml" or n.endswith("[Content_Types].xml") for n in names
        )
    if ext == ".pptx":
        return any(n.startswith("ppt/") for n in names)
    if ext == ".xlsx":
        return any(n.startswith("xl/") for n in names)
    if ext == ".epub":
        if "mimetype" not in names:
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                mime = zf.read("mimetype").decode("ascii", errors="ignore").strip()
            return mime == "application/epub+zip"
        except Exception:
            return False
    return False


def validate_magic_bytes(data: bytes, ext: str) -> str:
    """Ensure ``data`` matches ``ext``. Returns canonical MIME.

    Raises ValidationError with code ``invalid_mime`` on mismatch.
    """
    ext = (ext or "").lower()
    if not ext.startswith("."):
        ext = f".{ext}" if ext else ext
    if not data:
        raise ValidationError("empty_file", "Uploaded file is empty")

    kind = sniff_kind(data)
    expected_mime = CANONICAL_MIME.get(ext)
    if expected_mime is None:
        raise ValidationError("unsupported_type", f"Unsupported file type '{ext}'")

    ok = False
    if ext == ".pdf":
        ok = kind == "pdf"
    elif ext in (".png",):
        ok = kind == "png"
    elif ext in (".jpg", ".jpeg"):
        ok = kind == "jpeg"
    elif ext == ".gif":
        ok = kind == "gif"
    elif ext == ".webp":
        ok = kind == "webp"
    elif ext == ".txt":
        ok = kind == "text"
    elif ext in (".docx", ".pptx", ".xlsx", ".epub"):
        ok = kind == "zip" and _zip_matches_ext(data, ext)
    else:
        ok = False

    if not ok:
        raise ValidationError(
            "invalid_mime",
            f"File content does not match extension '{ext}' "
            f"(detected={kind or 'unknown'}).",
        )
    return expected_mime


def validate_magic_path(path: str, ext: str) -> str:
    with open(path, "rb") as fh:
        data = fh.read(max(SNIFF_BYTES, 256 * 1024))
    # ZIP subtype checks may need the full archive for small office files;
    # re-read all if file is modest and sniff was truncated.
    import os

    size = os.path.getsize(path)
    if ext.lower() in (".docx", ".pptx", ".xlsx", ".epub") and size <= 8 * 1024 * 1024:
        with open(path, "rb") as fh:
            data = fh.read()
    return validate_magic_bytes(data, ext)


def read_prefix(stream, nbytes: int = SNIFF_BYTES) -> bytes:
    """Read up to nbytes from a stream and rewind when possible."""
    data = stream.read(nbytes)
    if hasattr(stream, "seek"):
        try:
            stream.seek(0)
        except Exception:
            pass
    return data or b""
