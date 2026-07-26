"""Document-level counts, derived purely from already-extracted data —
no file access, no regex, no heuristics. Plain class, no interface (see
interfaces.py's module docstring): there is no plausible second
implementation of "count words" to swap in behind one.
"""

from .models import DocumentStatistics, DocumentStructure, ParsedDocument

# Standard reading-speed heuristic (words/minute) used to derive
# estimated_reading_time_minutes — not configurable per-document, so it
# lives here as a named constant rather than an inline magic number.
_WORDS_PER_MINUTE = 200


class StatisticsCalculator:
    """Aggregates counts from a ParsedDocument + DocumentStructure into a
    DocumentStatistics."""

    def calculate(self, parsed: ParsedDocument, structure: DocumentStructure) -> DocumentStatistics:
        word_count = len(parsed.raw_text.split())
        char_count = len(parsed.raw_text)

        return DocumentStatistics(
            page_count=parsed.page_count,
            word_count=word_count,
            char_count=char_count,
            estimated_reading_time_minutes=round(word_count / _WORDS_PER_MINUTE, 1),
            reference_count=len(structure.references),
            figure_count=len(structure.figures),
            table_count=len(structure.tables),
            heading_count=len(structure.heading_order),
            section_count=len(structure.normalized_headings),
        )
