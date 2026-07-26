"""Closed label sets for the Document Understanding Engine — string Enums
(not `str` constants scattered through the pipeline) so a typo in a
comparison fails at the call site (`SectionType.METHODS`, an
AttributeError on typo) instead of silently never matching (a plain
string comparison against `"methdos"` just returns False forever).

Each Enum subclasses `str` too (`class X(str, Enum)`), so a value still
serializes as its plain string ("methods", not "SectionType.METHODS")
anywhere this app already JSON-dumps a dataclass field — no special-cased
encoder needed.
"""

from enum import Enum


class DocumentLanguage(str, Enum):
    """ISO-639-1-ish codes for the handful of languages language.py's
    stopword heuristic can distinguish — see that module's own docstring
    for why this list is short and UNKNOWN is a real, expected outcome,
    not just an error case."""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    UNKNOWN = "unknown"


class HeadingType(str, Enum):
    """Which detection pattern matched a given heading — see headings.py.
    Ordered here the same as detection priority, for readability only
    (Enum members don't carry that ordering into comparisons)."""

    MARKDOWN = "markdown"
    NUMBERED = "numbered"
    UNDERLINE = "underline"
    BARE = "bare"


class SectionType(str, Enum):
    """Canonical section keys — the enum counterpart of
    backend.processing.normalization.NORMALIZED_SECTIONS' dict keys (see
    normalization.py's HeadingNormalizer, which wraps that exact dict).
    OTHER covers both "genuinely no known section" and "a future key
    NORMALIZED_SECTIONS gains that this enum doesn't have a member for
    yet" — from_key() below never raises for an unrecognized key, since
    that dict is documented as purely additive and this enum shouldn't
    need editing in lockstep with every entry added to it."""

    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    ABSTRACT = "abstract"
    REFERENCES = "references"
    ACKNOWLEDGMENTS = "acknowledgments"
    APPENDIX = "appendix"
    OTHER = "other"

    @classmethod
    def from_key(cls, key: "str | None") -> "SectionType":
        """Never raises. `key=None` (no normalization match) and an
        unrecognized string (a NORMALIZED_SECTIONS key added later with
        no matching enum member yet) both degrade to OTHER."""
        if key is None:
            return cls.OTHER
        try:
            return cls(key)
        except ValueError:
            return cls.OTHER


class ExtractionStatus(str, Enum):
    """One pipeline stage's outcome — see pipeline.py's StageLog."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class QualityLevel(str, Enum):
    """A human-readable bucket for DocumentQuality.confidence — derived
    via from_score(), never stored directly (see models.py's
    DocumentQuality.level property docstring for why)."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"

    @classmethod
    def from_score(cls, score: float) -> "QualityLevel":
        if score >= 0.85:
            return cls.EXCELLENT
        if score >= 0.65:
            return cls.GOOD
        if score >= 0.40:
            return cls.FAIR
        if score >= 0.15:
            return cls.POOR
        return cls.UNUSABLE


class DocumentFormat(str, Enum):
    """Detected from the input file's extension (see parser.py) — PDF is
    the only format this phase actually parses; the others exist so
    DocumentParser can report "recognized but not yet supported" instead
    of a generic failure, and so a future DOCX/HTML/XML parser has a real
    enum member to return rather than needing to add one later."""

    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    XML = "xml"
    UNKNOWN = "unknown"
