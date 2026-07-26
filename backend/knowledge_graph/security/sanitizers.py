"""Label and property sanitization for graph export safety."""

import re
from typing import Any

_HTML_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_CYPHER_UNSAFE_RE = re.compile(r"[`'\\]")


class LabelSanitizer:
    def __init__(self, max_length: int = 500) -> None:
        self.max_length = max_length

    def sanitize(self, label: str) -> str:
        cleaned = _CONTROL_CHAR_RE.sub("", label or "")
        cleaned = _HTML_TAG_RE.sub("", cleaned)
        cleaned = cleaned.replace("\n", " ").strip()
        return cleaned[: self.max_length]


def sanitize_properties(properties: dict[str, Any], max_string_length: int = 2000) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (properties or {}).items():
        safe_key = re.sub(r"[^a-zA-Z0-9_]", "_", str(key))[:64]
        if isinstance(value, str):
            cleaned = _CONTROL_CHAR_RE.sub("", value)
            cleaned = _HTML_TAG_RE.sub("", cleaned)
            safe[safe_key] = cleaned[:max_string_length]
        elif isinstance(value, (int, float, bool)) or value is None:
            safe[safe_key] = value
        elif isinstance(value, (list, tuple)):
            safe[safe_key] = [str(v)[:max_string_length] for v in value[:50]]
        else:
            safe[safe_key] = str(value)[:max_string_length]
    return safe


def escape_cypher_string(value: str) -> str:
    return _CYPHER_UNSAFE_RE.sub(lambda m: "\\" + m.group(0), value or "")
