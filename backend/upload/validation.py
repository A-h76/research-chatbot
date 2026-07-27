"""Pure validation helpers for uploads — no Flask/DB imports.

PR3: shared extension allowlist for session + JWT paths, plus magic-byte
and optional ClamAV entry points.
"""

from __future__ import annotations

import os

from werkzeug.utils import secure_filename

from .clamav import scan_bytes, scan_path
from .errors import ValidationError
from .magic_bytes import validate_magic_bytes, validate_magic_path

DOCUMENT_EXTENSIONS = {".pdf", ".epub", ".docx", ".txt", ".pptx", ".xlsx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

DEFAULT_MAX_UPLOAD_MB = 50
MAX_DOCUMENT_UPLOAD_MB = int(os.environ.get("MAX_DOCUMENT_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB)))

__all__ = [
    "ALLOWED_EXTENSIONS",
    "DOCUMENT_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "MAX_DOCUMENT_UPLOAD_MB",
    "ValidationError",
    "kind_for_extension",
    "safe_filename",
    "validate_extension",
    "validate_size",
    "validate_upload_bytes",
    "validate_upload_path",
]


def validate_extension(filename: str, *, allowed=None) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    allow = allowed if allowed is not None else ALLOWED_EXTENSIONS
    if ext not in allow:
        raise ValidationError(
            "unsupported_type",
            f"Unsupported file type '{ext or '(none)'}'. " f"Allowed: {', '.join(sorted(allow))}",
        )
    return ext


def validate_size(size_bytes: int, max_mb: int = MAX_DOCUMENT_UPLOAD_MB) -> None:
    if size_bytes <= 0:
        raise ValidationError("empty_file", "Uploaded file is empty")
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError("too_large", f"File exceeds the {max_mb} MB limit")


def safe_filename(original: str, ext: str) -> str:
    """secure_filename() can return "" for a name made entirely of
    characters it strips (e.g. an all-unicode filename) — fall back to a
    generic name so the storage key never ends in an empty segment."""
    cleaned = secure_filename(original or "")
    return cleaned if cleaned else f"upload{ext}"


def kind_for_extension(ext: str) -> str:
    return "image" if ext.lower() in IMAGE_EXTENSIONS else "document"


def validate_upload_bytes(
    data: bytes,
    filename: str,
    *,
    allowed=None,
    scan: bool = True,
) -> tuple[str, str]:
    """Extension + magic (+ optional ClamAV). Returns ``(ext, canonical_mime)``."""
    ext = validate_extension(filename, allowed=allowed)
    validate_size(len(data))
    mime = validate_magic_bytes(data, ext)
    if scan:
        scan_bytes(data, filename=filename)
    return ext, mime


def validate_upload_path(
    path: str,
    filename: str,
    *,
    allowed=None,
    scan: bool = True,
    size_bytes: int | None = None,
    max_mb: int = MAX_DOCUMENT_UPLOAD_MB,
) -> tuple[str, str]:
    """Extension + magic (+ optional ClamAV) for a file on disk."""
    ext = validate_extension(filename, allowed=allowed)
    size = size_bytes if size_bytes is not None else os.path.getsize(path)
    validate_size(size, max_mb=max_mb)
    mime = validate_magic_path(path, ext)
    if scan:
        scan_path(path, filename=filename)
    return ext, mime
