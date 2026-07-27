"""Content sanitization and safe template filling.

Never use str.format() / f-strings with untrusted document content —
userers can contain `{` / `}` that crash format or inject keys.
safe_fill_template only substitutes an explicit whitelist of keys via
plain str.replace after sanitizing values.
"""

import re
from typing import Optional

_HTML_TAG_RE = re.compile(r"<[^>]*>")
_MARKDOWN_SPECIAL_RE = re.compile(r"([*_`\[\]()#>~])")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text or "")


def escape_markdown(text: str) -> str:
    return _MARKDOWN_SPECIAL_RE.sub(r"\\\1", text or "")


class ContentSanitizer:
    def __init__(self, max_length: int = 10000, strip_html_tags: bool = True) -> None:
        self.max_length = max_length
        self.strip_html_tags = strip_html_tags

    def sanitize(self, content: str) -> str:
        cleaned = _CONTROL_CHAR_RE.sub("", content or "")
        if self.strip_html_tags:
            cleaned = strip_html(cleaned)
        cleaned = escape_markdown(cleaned)
        # Neutralize residual braces so leftover template syntax cannot
        # be interpreted by a later fill pass.
        cleaned = cleaned.replace("{", "(").replace("}", ")")
        return cleaned[: self.max_length]


def safe_fill_template(
    template: str,
    variables: dict[str, str],
    allowed_keys: Optional[set[str]] = None,
) -> str:
    """Substitute `{key}` placeholders for whitelisted keys only.

    Unknown placeholders are replaced with an empty string (never left
    as raw `{foo}` that a later naive format could interpret). Values
    are inserted as-is — callers must sanitize first.
    """
    allowed = allowed_keys if allowed_keys is not None else set(variables.keys())
    safe_vars = {k: (variables.get(k) or "") for k in allowed}

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in allowed:
            return ""
        return safe_vars.get(key, "")

    return _PLACEHOLDER_RE.sub(_replace, template or "")
