"""Heading normalization rules — the single place new section types get
added (see this module's own docstring on NORMALIZED_SECTIONS below and
package docstring's "Extensibility" note). Nothing in sections.py hardcodes
a section name; it only ever calls normalize_heading() and reacts to
whatever key (or None) comes back.
"""

import re
from dataclasses import dataclass
from typing import Optional

# Canonical section key -> every raw heading variant academic papers use
# for it. Purely additive: to recognise a new section type (e.g. "ethics"),
# add one more `"ethics": [...]` entry here — sections.py and quality.py
# never need to change, since both work off whatever keys this dict
# happens to contain at call time, not a fixed enum.
NORMALIZED_SECTIONS: dict[str, list[str]] = {
    "introduction": [
        "introduction",
        "background",
        "context",
        "preliminaries",
    ],
    "methods": [
        "methods",
        "methodology",
        "materials and methods",
        "experimental design",
        "study design",
        "procedure",
    ],
    "results": [
        "results",
        "findings",
        "experimental results",
        "outcomes",
    ],
    "discussion": [
        "discussion",
        "conclusion",
        "conclusions",
        "summary",
        "interpretation",
    ],
    "abstract": ["abstract", "summary"],
    "references": ["references", "bibliography", "works cited"],
    "acknowledgments": ["acknowledgments", "acknowledgements"],
    "appendix": ["appendix", "supplementary", "supplemental"],
}

# "summary" legitimately means two different things above (a discussion-style
# wrap-up, and an abstract synonym) — discussion is checked first so a raw
# heading literally titled "Summary" normalizes to "discussion" (the far
# more common academic use: a closing summary section), not "abstract".
# _build_keyword_index()'s "first assignment wins, no overwrite" behavior
# is what makes this ordering matter; it's encoded here, once, rather than
# as an implicit side effect a future contributor could reorder by accident.
_AMBIGUOUS_KEYWORD_PRIORITY: tuple[str, ...] = ("discussion", "abstract")


@dataclass
class NormalizationMatch:
    """Result of normalize_heading() — a structured outcome (rule #11)
    rather than a bare Optional[str], so callers get *why* a heading
    matched (or didn't) without re-deriving it themselves.

    Attributes:
        normalized_key: The canonical section key, or None if nothing
            in NORMALIZED_SECTIONS matched closely enough.
        confidence: 1.0 for an exact keyword match, 0.6 for a substring/
            partial match, 0.0 when normalized_key is None.
        reasoning: Human-readable explanation, e.g. "exact match on
            keyword 'methods'" or "no known section keyword found".
    """

    normalized_key: Optional[str]
    confidence: float
    reasoning: str


def _clean_heading_text(raw_heading: str) -> str:
    """Strips numbering/markdown/punctuation noise so "2.1 Methods" and
    "## Methods" both compare equal to the plain keyword "methods".
    Deliberately conservative — this must never eat real heading words,
    only leading numerals/symbols and surrounding whitespace."""
    text = raw_heading.strip().lstrip("#").strip()
    # Leading numbering: "1.", "2.1", "II.", "(3)" — a run of digits/roman
    # numerals/punctuation followed by whitespace, at the very start only.
    text = re.sub(r"^[\divxlcIVXLC()./-]+\s+", "", text)
    return text.strip().strip(":").strip().lower()


def _build_keyword_index() -> dict[str, str]:
    """Flattens NORMALIZED_SECTIONS into keyword -> normalized_key for O(1)
    lookup. Rebuilt fresh from the module-level dict on every call (this
    runs once per process at import time via _KEYWORD_INDEX below, and
    again only if a caller explicitly wants a live rebuild after mutating
    NORMALIZED_SECTIONS at runtime — cheap enough either way, this dict
    never grows past a few dozen entries).

    First assignment wins for a keyword shared by two normalized keys
    (see _AMBIGUOUS_KEYWORD_PRIORITY above) — iterating normalized keys in
    that priority order first, then the rest of NORMALIZED_SECTIONS in
    their natural order, makes that deterministic rather than dependent on
    dict insertion order."""
    index: dict[str, str] = {}
    ordered_keys = list(_AMBIGUOUS_KEYWORD_PRIORITY) + [
        k for k in NORMALIZED_SECTIONS if k not in _AMBIGUOUS_KEYWORD_PRIORITY
    ]
    for normalized_key in ordered_keys:
        for keyword in NORMALIZED_SECTIONS.get(normalized_key, ()):
            index.setdefault(keyword.lower(), normalized_key)
    return index


_KEYWORD_INDEX: dict[str, str] = _build_keyword_index()


def normalize_heading(raw_heading: str) -> NormalizationMatch:
    """Maps a raw heading (as it appeared in the document) to one of
    NORMALIZED_SECTIONS' canonical keys.

    Two-tier match, cheapest/most-confident first:
      1. Exact match: the cleaned heading text equals a known keyword
         verbatim (confidence 1.0).
      2. Partial match: a known keyword appears as a substring of the
         cleaned heading, or vice versa (confidence 0.6) — catches
         real-world variants like "1. Introduction and Motivation" or
         "Methodology Overview" that an exact match would miss.
      3. No match: normalized_key=None, confidence=0.0.
    """
    cleaned = _clean_heading_text(raw_heading)
    if not cleaned:
        return NormalizationMatch(None, 0.0, "empty heading text")

    exact = _KEYWORD_INDEX.get(cleaned)
    if exact is not None:
        return NormalizationMatch(exact, 1.0, f"exact match on keyword {cleaned!r}")

    for keyword, normalized_key in _KEYWORD_INDEX.items():
        if keyword in cleaned or cleaned in keyword:
            return NormalizationMatch(
                normalized_key, 0.6, f"partial match: {cleaned!r} contains/within keyword {keyword!r}"
            )

    return NormalizationMatch(None, 0.0, f"no known section keyword found in {cleaned!r}")
