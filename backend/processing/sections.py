"""Heading detection and normalization.

Detects headings using four patterns, tried in this priority order per
line (first match wins, so a line is never double-counted):
  1. Markdown-style: "## Heading"
  2. Numbered: "1. Introduction", "2.1 Methods", "IV. Discussion"
  3. Underline-style: "Heading" followed by a line of "===" or "---"
  4. Bare line: a short, standalone line whose text normalizes against
     NORMALIZED_SECTIONS with reasonable confidence (catches the common
     real-PDF case of a heading with no markup at all, just its own line
     — "Introduction", "METHODS", ...).

Normalization itself (raw heading -> canonical key) is entirely
normalization.py's job; this module only finds heading-shaped lines and
hands their text to normalize_heading(), so a new heading *pattern* is a
change here, while a new *section type* (e.g. teaching normalize_heading
about "ethics" headings) never requires touching this file at all.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .models import SectionExtractionResult, SectionMatch
from .normalization import normalize_heading

_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_NUMBERED_HEADING_RE = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.)\s+([A-Z][^\n]{1,78})$")
_UNDERLINE_RULE_RE = re.compile(r"^[=-]{3,}$")

# A "bare" heading (no markdown/numbering/underline) has no structural
# signal backing it up at all, so it requires an EXACT normalize_heading()
# match (confidence 1.0), not the 0.6 partial/substring match numbered and
# markdown headings are still allowed to use — a partial match here false-
# positived on real prose during testing ("This is the introduction with
# background context." partially matches keyword "introduction" and is
# under the 60-char cutoff). The length cutoff alone isn't a reliable
# enough guard; requiring the exact-match tier is.
_MAX_BARE_HEADING_LEN = 60
_MIN_BARE_HEADING_CONFIDENCE = 1.0


@dataclass
class _HeadingHit:
    raw_heading: str
    line_index: int
    consumed_lines: int  # 1 normally; 2 for underline-style (heading + rule line)


def _detect_heading(lines: list[str], i: int) -> Optional[_HeadingHit]:
    """Checks whether `lines[i]` (possibly together with `lines[i + 1]`)
    is a heading, per this module's own docstring priority order."""
    line = lines[i].strip()
    if not line:
        return None

    md_match = _MARKDOWN_HEADING_RE.match(line)
    if md_match:
        return _HeadingHit(md_match.group(1).strip(), i, 1)

    numbered_match = _NUMBERED_HEADING_RE.match(line)
    if numbered_match:
        return _HeadingHit(line, i, 1)

    if i + 1 < len(lines) and _UNDERLINE_RULE_RE.match(lines[i + 1].strip()):
        return _HeadingHit(line, i, 2)

    if len(line) <= _MAX_BARE_HEADING_LEN:
        match = normalize_heading(line)
        if match.confidence >= _MIN_BARE_HEADING_CONFIDENCE:
            return _HeadingHit(line, i, 1)

    return None


class SectionExtractor:
    """Detects headings in plain document text and maps each one to a
    normalized section key (see normalization.py)."""

    def extract(self, text: str) -> SectionExtractionResult:
        lines = text.split("\n")

        hits: list[_HeadingHit] = []
        i = 0
        while i < len(lines):
            hit = _detect_heading(lines, i)
            if hit:
                hits.append(hit)
                i += hit.consumed_lines
            else:
                i += 1

        if not hits:
            return SectionExtractionResult(
                section_order=[], raw_sections={}, normalized_sections={}, matches=[], overall_confidence=0.0
            )

        section_order: list[str] = []
        raw_sections: dict[str, str] = {}
        normalized_sections: dict[str, str] = {}
        matches: list[SectionMatch] = []

        for idx, hit in enumerate(hits):
            content_start = hit.line_index + hit.consumed_lines
            content_end = hits[idx + 1].line_index if idx + 1 < len(hits) else len(lines)
            content = "\n".join(lines[content_start:content_end]).strip()

            section_order.append(hit.raw_heading)
            raw_sections[self._unique_key(raw_sections, hit.raw_heading)] = content

            norm = normalize_heading(hit.raw_heading)
            matches.append(SectionMatch(hit.raw_heading, norm.normalized_key, norm.confidence, norm.reasoning))
            if norm.normalized_key:
                if norm.normalized_key in normalized_sections:
                    # A second heading normalizing to an already-seen key
                    # (e.g. both "Conclusion" and "Summary" -> "discussion")
                    # appends rather than overwrites, so no content is lost.
                    normalized_sections[norm.normalized_key] += "\n\n" + content
                else:
                    normalized_sections[norm.normalized_key] = content

        overall_confidence = sum(m.confidence for m in matches) / len(matches)

        return SectionExtractionResult(
            section_order=section_order,
            raw_sections=raw_sections,
            normalized_sections=normalized_sections,
            matches=matches,
            overall_confidence=overall_confidence,
        )

    @staticmethod
    def _unique_key(existing: dict[str, str], raw_heading: str) -> str:
        """Two raw headings with identical text (e.g. a repeated
        "Discussion" in an appendix) must not silently overwrite each
        other in raw_sections — disambiguated with a " (2)", " (3)", ...
        suffix rather than dropped."""
        if raw_heading not in existing:
            return raw_heading
        suffix = 2
        while f"{raw_heading} ({suffix})" in existing:
            suffix += 1
        return f"{raw_heading} ({suffix})"
