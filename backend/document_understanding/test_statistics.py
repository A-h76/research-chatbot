from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import DocumentStructure, ParsedDocument
from backend.document_understanding.statistics import StatisticsCalculator


def test_computes_counts_from_parsed_and_structure():
    parsed = ParsedDocument(raw_text="one two three four five six seven eight nine ten", page_count=3)
    structure = DocumentStructure(
        heading_order=["Intro", "Methods", "Results"],
        normalized_headings={SectionType.INTRODUCTION: "x", SectionType.METHODS: "y"},
        references=["[1] a", "[2] b"],
        figures=[{}],
        tables=[],
    )

    stats = StatisticsCalculator().calculate(parsed, structure)

    assert stats.page_count == 3
    assert stats.word_count == 10
    assert stats.char_count == len(parsed.raw_text)
    assert stats.reference_count == 2
    assert stats.figure_count == 1
    assert stats.table_count == 0
    assert stats.heading_count == 3
    assert stats.section_count == 2


def test_empty_document_yields_all_zero_stats():
    stats = StatisticsCalculator().calculate(ParsedDocument(), DocumentStructure())
    assert stats.word_count == 0
    assert stats.char_count == 0
    assert stats.estimated_reading_time_minutes == 0.0
    assert stats.heading_count == 0
