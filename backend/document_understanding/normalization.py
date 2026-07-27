"""Heading normalization — maps a raw heading's text to a canonical
SectionType.

True reuse, not a reimplementation (see package docstring's reuse
table): wraps backend.processing.normalization.normalize_heading()
directly. That function's own NORMALIZED_SECTIONS dict remains the one
place a new section type gets added — nothing here or in
NORMALIZED_SECTIONS' own module needs to change to recognize one; only
enums.SectionType gains a new member (and even that is optional in the
short term, since SectionType.from_key() degrades an unrecognized key to
OTHER rather than raising).
"""

from backend.processing.normalization import normalize_heading as _legacy_normalize_heading

from .enums import SectionType
from .interfaces import BaseHeadingNormalizer
from .models import NormalizedHeading


class HeadingNormalizer(BaseHeadingNormalizer):
    """Thin, stateless wrapper around backend.processing's
    normalize_heading() — upgrades its string-or-None result to a
    SectionType member."""

    def normalize(self, raw_heading: str) -> NormalizedHeading:
        match = _legacy_normalize_heading(raw_heading)
        return NormalizedHeading(
            section_type=SectionType.from_key(match.normalized_key),
            confidence=match.confidence,
            reasoning=match.reasoning,
        )
