"""Pure validation helpers for POST /api/documents/upload — no Flask/DB
imports, so these are unit-testable without a request context."""

import os

from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {".pdf", ".epub", ".docx", ".txt"}
DEFAULT_MAX_UPLOAD_MB = 50
MAX_DOCUMENT_UPLOAD_MB = int(os.environ.get("MAX_DOCUMENT_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB)))


class ValidationError(Exception):
    """.code is machine-readable (goes in the JSON error field), .message
    is the human-readable string returned alongside it."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_extension(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "unsupported_type",
            f"Unsupported file type '{ext or '(none)'}'. " f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
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
