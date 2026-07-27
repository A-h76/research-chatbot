"""Input sanitization for rationale/reasoning text that ends up in an
audit trail or grade description — these strings sometimes get rendered
in a UI or exported as a report, so unlike backend.medical_understanding's
own sanitizers.py (which only guards regex matching), this module also
strips HTML and escapes markdown special characters, not just control
characters.
"""

import re
from typing import Optional

_HTML_TAG_RE = re.compile(r"<[^>]*>")
_MARKDOWN_SPECIAL_RE = re.compile(r"([*_`\[\]()#>~])")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text or "")


def escape_markdown(text: str) -> str:
    return _MARKDOWN_SPECIAL_RE.sub(r"\\\1", text or "")


class Sanitizer:
    """See module docstring."""

    def __init__(self, max_rationale_length: int = 1000) -> None:
        self.max_rationale_length = max_rationale_length

    def sanitize_rationale(self, text: str) -> str:
        cleaned = _CONTROL_CHAR_RE.sub("", text or "")
        cleaned = strip_html(cleaned)
        cleaned = escape_markdown(cleaned)
        return cleaned[: self.max_rationale_length]


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Control-character stripping only — for text that never gets
    rendered as HTML/markdown (e.g. a plain log message)."""
    cleaned = _CONTROL_CHAR_RE.sub("", text or "")
    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned
