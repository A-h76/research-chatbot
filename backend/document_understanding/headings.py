"""Heading detection — finds heading-shaped lines in plain text, without
judging what section each one is (that's normalization.py's job).

Ports (does not wrap — see package docstring's reuse table) the four
detection patterns backend.processing.sections.SectionExtractor already
uses internally, adding character-offset tracking that module has no
reason to carry (its own SectionExtractionResult has no offset fields).
Priority order per line, first match wins, same as the original: (1)
markdown "## Heading", (2) numbered "1. Introduction"/"IV. Discussion",
(3) underline-style "Heading" + a "===="/"----" rule line, (4) a bare,
short, standalone line whose text alone strongly matches a known section
keyword (see normalization.py) — the common case for a real PDF's
heading with no markup at all.
"""

import re
from typing import Optional

from .enums import HeadingType
from .interfaces import BaseHeadingDetector
from .models import HeadingCandidate
from .normalization import HeadingNormalizer

_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_NUMBERED_HEADING_RE = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.)\s+([A-Z][^\n]{1,78})$")
_UNDERLINE_RULE_RE = re.compile(r"^[=-]{3,}$")

# Same reasoning as backend.processing.sections' identical constants: a
# bare heading has no structural signal backing it up, so it requires a
# short line AND an exact (not partial/substring) keyword match.
_MAX_BARE_HEADING_LEN = 60
_MIN_BARE_HEADING_CONFIDENCE = 1.0

# One shared instance — HeadingNormalizer is a thin, stateless wrapper
# (see normalization.py), safe to reuse across every detect() call rather
# than constructing one per line.
_normalizer = HeadingNormalizer()


class HeadingDetector(BaseHeadingDetector):
    """Detects heading-shaped lines in `text`, returning each as a
    HeadingCandidate with its character offsets into that same string."""

    def detect(self, text: str) -> list[HeadingCandidate]:
        lines = text.split("\n")
        line_offsets = self._line_start_offsets(lines)

        candidates: list[HeadingCandidate] = []
        i = 0
        while i < len(lines):
            hit = self._detect_at(lines, i)
            if hit is None:
                i += 1
                continue
            raw_heading, heading_type, consumed = hit
            start = line_offsets[i]
            end = line_offsets[i + consumed - 1] + len(lines[i + consumed - 1])
            candidates.append(HeadingCandidate(raw_heading, heading_type, start, end))
            i += consumed

        return candidates

    @staticmethod
    def _line_start_offsets(lines: list[str]) -> list[int]:
        offsets = []
        pos = 0
        for line in lines:
            offsets.append(pos)
            pos += len(line) + 1  # +1 for the '\n' split() consumed
        return offsets

    @staticmethod
    def _detect_at(lines: list[str], i: int) -> Optional[tuple[str, HeadingType, int]]:
        line = lines[i].strip()
        if not line:
            return None

        md_match = _MARKDOWN_HEADING_RE.match(line)
        if md_match:
            return md_match.group(1).strip(), HeadingType.MARKDOWN, 1

        numbered_match = _NUMBERED_HEADING_RE.match(line)
        if numbered_match:
            return line, HeadingType.NUMBERED, 1

        if i + 1 < len(lines) and _UNDERLINE_RULE_RE.match(lines[i + 1].strip()):
            return line, HeadingType.UNDERLINE, 2

        if len(line) <= _MAX_BARE_HEADING_LEN:
            match = _normalizer.normalize(line)
            if match.confidence >= _MIN_BARE_HEADING_CONFIDENCE:
                return line, HeadingType.BARE, 1

        return None
