"""Input sanitization — defensive text cleanup before pattern matching.

Not guarding against XSS/SQL injection (this pipeline never touches a
browser or a database query) — the real risks here are the same class
backend.document_understanding's own quality.py already watches for:
control characters/null bytes that break regex matching or corrupt
evidence snippets, and paragraphs long enough to make matching slow or
an evidence snippet unreadable.
"""

import re
from typing import Optional

from ..config import MedicalUnderstandingConfig

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Strips control characters and (optionally) truncates to
    max_length — never raises, always returns a usable string."""
    cleaned = _CONTROL_CHAR_RE.sub("", text or "")
    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def sanitize_paragraph(text: str, config: MedicalUnderstandingConfig) -> str:
    return sanitize_text(text, max_length=config.max_paragraph_size)


def clamp_context(text: str, config: MedicalUnderstandingConfig) -> str:
    return sanitize_text(text, max_length=config.max_context_length)
