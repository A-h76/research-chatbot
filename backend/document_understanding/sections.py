"""Section building — combines heading detection + normalization into a
full DocumentStructure.

Not a wrap of backend.processing.sections.SectionExtractor (see package
docstring's reuse table): that class's SectionExtractionResult has no
character-offset data to adapt, and section_offsets (the field this
package adds specifically for traceability.py) can only be computed
here, where the raw HeadingCandidate offsets are still in scope. The
grouping/disambiguation logic itself (unique raw-heading keys, append-
on-duplicate-normalized-key) is ported from that same class, which is
the tested, existing behavior for how sections merge.
"""

from .enums import HeadingType, SectionType
from .interfaces import BaseHeadingDetector, BaseHeadingNormalizer, BaseSectionBuilder
from .models import DocumentStructure


class SectionBuilder(BaseSectionBuilder):
    """Detects headings via the injected BaseHeadingDetector, normalizes
    each via the injected BaseHeadingNormalizer, and groups the text
    between consecutive headings into that heading's content."""

    def __init__(self, detector: BaseHeadingDetector, normalizer: BaseHeadingNormalizer) -> None:
        self._detector = detector
        self._normalizer = normalizer

    def build(self, text: str) -> DocumentStructure:
        candidates = self._detector.detect(text)
        if not candidates:
            return DocumentStructure()

        heading_order: list[str] = []
        raw_headings: dict[str, str] = {}
        normalized_headings: dict[SectionType, str] = {}
        section_offsets: dict[str, tuple[int, int]] = {}
        heading_types: dict[str, HeadingType] = {}
        section_types: dict[str, SectionType] = {}
        confidences: list[float] = []

        for idx, candidate in enumerate(candidates):
            content_start = candidate.end_offset
            content_end = candidates[idx + 1].start_offset if idx + 1 < len(candidates) else len(text)
            content, span_start, span_end = self._strip_span(text, content_start, content_end)

            key = self._unique_key(raw_headings, candidate.raw_heading)
            heading_order.append(candidate.raw_heading)
            raw_headings[key] = content
            section_offsets[key] = (span_start, span_end)
            heading_types[key] = candidate.heading_type

            normalized = self._normalizer.normalize(candidate.raw_heading)
            confidences.append(normalized.confidence)
            section_types[key] = normalized.section_type
            if normalized.section_type != SectionType.OTHER:
                if normalized.section_type in normalized_headings:
                    # A second heading normalizing to an already-seen type
                    # (e.g. both "Conclusion" and "Summary" -> DISCUSSION)
                    # appends rather than overwrites, so no content is lost.
                    normalized_headings[normalized.section_type] += "\n\n" + content
                else:
                    normalized_headings[normalized.section_type] = content

        references_blob = normalized_headings.get(SectionType.REFERENCES, "")
        references = [line.strip() for line in references_blob.splitlines() if line.strip()]

        return DocumentStructure(
            heading_order=heading_order,
            raw_headings=raw_headings,
            normalized_headings=normalized_headings,
            section_offsets=section_offsets,
            heading_types=heading_types,
            section_types=section_types,
            appendix=normalized_headings.get(SectionType.APPENDIX),
            references=references,
            tables=[],
            figures=[],
            supplementary_material=None,
            confidence=sum(confidences) / len(confidences),
        )

    @staticmethod
    def _strip_span(text: str, start: int, end: int) -> tuple[str, int, int]:
        """Content between two heading offsets includes the newline(s)
        around it; this trims that whitespace while keeping (start, end)
        accurate to the trimmed result, so section_offsets points at the
        actual content text, not at surrounding blank lines."""
        raw = text[start:end]
        left_trimmed = raw.lstrip()
        left_trim = len(raw) - len(left_trimmed)
        stripped = left_trimmed.rstrip()
        span_start = start + left_trim
        return stripped, span_start, span_start + len(stripped)

    @staticmethod
    def _unique_key(existing: dict[str, str], raw_heading: str) -> str:
        """Two raw headings with identical text (e.g. a repeated
        "Discussion" in an appendix) must not silently overwrite each
        other — disambiguated with a " (2)", " (3)", ... suffix rather
        than dropped."""
        if raw_heading not in existing:
            return raw_heading
        suffix = 2
        while f"{raw_heading} ({suffix})" in existing:
            suffix += 1
        return f"{raw_heading} ({suffix})"
