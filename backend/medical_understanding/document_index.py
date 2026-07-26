"""Shared document index — pre-processed ProcessedDocument sections,
built once per pipeline run and reused by every extractor (see package
docstring's "Document Index (Prevents Scans)" design principle).

Paragraph offsets are computed from backend.document_understanding's own
DocumentStructure.section_offsets/section_types (Phase 1.1's already-
computed per-heading character ranges) — never by re-scanning or
`.find()`-ing content back into full_text, which could go wrong on
duplicate/similar content. tables/figures are always empty: Phase 1.1's
own DocumentStructure.tables/figures are themselves always empty lists
today (a documented Phase 1.1 non-goal — no layout/table-structure
analysis exists yet), so there is nothing to index here either; the
fields exist for a future Phase 1.1 upgrade to populate without a shape
change here.
"""

from dataclasses import dataclass, field
from typing import Optional

from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import EvidenceReference, PageOffset, ProcessedDocument
from backend.document_understanding.utils import page_at_offset, snippet_at

from .security import RegexGuard


@dataclass(frozen=True)
class Paragraph:
    """One paragraph's text plus its exact character range within
    ProcessedDocument.full_text — the traceability hook every extractor
    builds its EvidenceReference from."""

    text: str
    section_type: SectionType
    start: int
    end: int
    paragraph_index: int


@dataclass(frozen=True)
class Table:
    """Always unpopulated today — see module docstring."""

    caption: str
    content: str
    page: Optional[int] = None


@dataclass(frozen=True)
class Figure:
    """Always unpopulated today — see module docstring."""

    caption: str
    page: Optional[int] = None


@dataclass(frozen=True)
class Reference:
    """One raw reference-list entry — Phase 1.1's own DocumentStructure.
    references, wrapped with its position. No citation parsing (author/
    year/title extraction) is attempted — that's out of this phase's
    scope, same as Phase 1.1's own identical non-goal for this field."""

    index: int
    raw_text: str


@dataclass(frozen=True)
class TextMatch:
    """One find_text() hit — `start`/`end` are offsets within
    `paragraph.text`; add `paragraph.start` to get the offset within
    ProcessedDocument.full_text."""

    paragraph: Paragraph
    start: int
    end: int
    matched_text: str

    @property
    def document_range(self) -> tuple[int, int]:
        return (self.paragraph.start + self.start, self.paragraph.start + self.end)


@dataclass
class DocumentIndex:
    """See module docstring. One instance per pipeline run, built by
    build_document_index() below — never constructed by an extractor
    itself (matches this package's "no component instantiates another
    directly" rule)."""

    sections: dict[SectionType, list[Paragraph]] = field(default_factory=dict)
    methods_sections: list[Paragraph] = field(default_factory=list)
    results_sections: list[Paragraph] = field(default_factory=list)
    discussion_sections: list[Paragraph] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    figures: list[Figure] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    full_text: str = ""
    page_ranges: list[PageOffset] = field(default_factory=list)
    regex_guard: RegexGuard = field(default_factory=RegexGuard, repr=False, compare=False)
    _find_text_cache: dict[tuple, list[TextMatch]] = field(default_factory=dict, repr=False, compare=False)

    def get_paragraphs(self, section: SectionType) -> list[Paragraph]:
        return self.sections.get(section, [])

    def evidence_for(self, match: TextMatch, confidence: float) -> EvidenceReference:
        """Builds a full EvidenceReference for one find_text() hit —
        the one place page/paragraph/snippet lookup logic lives, so no
        extractor reimplements it. Reuses backend.document_understanding.
        utils' own page_at_offset()/snippet_at() (Phase 1.1's own
        traceability helpers) rather than a second implementation."""
        start, end = match.document_range
        return EvidenceReference(
            page=page_at_offset(self.page_ranges, start),
            section=match.paragraph.section_type,
            paragraph=match.paragraph.paragraph_index,
            character_range=(start, end),
            text_snippet=snippet_at(self.full_text, start, end),
            confidence=confidence,
        )

    def find_text(self, pattern: str, sections: list[SectionType]) -> list[TextMatch]:
        """Cached by (pattern, sections) — a second extractor asking for
        the same pattern over the same sections gets the cached result
        instead of re-matching (see package docstring)."""
        cache_key = (pattern, tuple(sorted(section.value for section in sections)))
        if cache_key in self._find_text_cache:
            return self._find_text_cache[cache_key]

        matches = self._search(pattern, sections)
        self._find_text_cache[cache_key] = matches
        return matches

    def _search(self, pattern: str, sections: list[SectionType]) -> list[TextMatch]:
        compiled = self.regex_guard.safe_compile(pattern)
        if compiled is None:
            return []

        matches: list[TextMatch] = []
        for section in sections:
            for paragraph in self.sections.get(section, []):
                for match in self.regex_guard.safe_finditer(compiled, paragraph.text):
                    matches.append(
                        TextMatch(
                            paragraph=paragraph, start=match.start(), end=match.end(), matched_text=match.group(0)
                        )
                    )
        return matches


def build_document_index(document: ProcessedDocument, regex_guard: Optional[RegexGuard] = None) -> DocumentIndex:
    """Builds a DocumentIndex from an already-processed ProcessedDocument
    — no PDF re-parsing, no re-running Phase 1.1's own section/heading
    detection."""
    guard = regex_guard or RegexGuard()
    structure = document.structure

    sections: dict[SectionType, list[Paragraph]] = {
        section_type: _paragraphs_for_section(document, section_type) for section_type in structure.normalized_headings
    }
    references = [Reference(index=i, raw_text=raw) for i, raw in enumerate(structure.references)]

    return DocumentIndex(
        sections=sections,
        methods_sections=sections.get(SectionType.METHODS, []),
        results_sections=sections.get(SectionType.RESULTS, []),
        discussion_sections=sections.get(SectionType.DISCUSSION, []),
        tables=[],
        figures=[],
        references=references,
        full_text=document.full_text,
        page_ranges=document.page_ranges,
        regex_guard=guard,
    )


def _paragraphs_for_section(document: ProcessedDocument, section_type: SectionType) -> list[Paragraph]:
    structure = document.structure
    raw_keys = [key for key, mapped_type in structure.section_types.items() if mapped_type == section_type]

    paragraphs: list[Paragraph] = []
    paragraph_index = 0
    for raw_key in raw_keys:
        span = structure.section_offsets.get(raw_key)
        if span is None:
            continue
        for para_start, para_end in _split_paragraph_offsets(document.full_text, *span):
            paragraphs.append(
                Paragraph(
                    text=document.full_text[para_start:para_end],
                    section_type=section_type,
                    start=para_start,
                    end=para_end,
                    paragraph_index=paragraph_index,
                )
            )
            paragraph_index += 1
    return paragraphs


def _split_paragraph_offsets(full_text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Splits [start, end) into "\\n\\n"-separated paragraph spans,
    matching backend.document_understanding.traceability's own
    paragraph-boundary convention — trims surrounding whitespace per
    paragraph so offsets point at real content, not blank lines."""
    spans: list[tuple[int, int]] = []
    pos = start
    for raw_paragraph in full_text[start:end].split("\n\n"):
        left_trim = len(raw_paragraph) - len(raw_paragraph.lstrip())
        stripped = raw_paragraph.strip()
        if stripped:
            span_start = pos + left_trim
            spans.append((span_start, span_start + len(stripped)))
        pos += len(raw_paragraph) + 2  # +2 for the "\n\n" separator consumed by split()
    return spans
