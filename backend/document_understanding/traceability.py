"""Evidence traceability — maps extracted facts back to where they came
from in the source document.

Genuinely new (see package docstring's reuse table — nothing in
backend.processing computes this). Two families of fact, located two
different ways:

- Section facts (structure.section.<type>) already have an exact
  character range from sections.py's own offset tracking — no searching
  needed, confidence is always 1.0.
- Scalar metadata facts (metadata.<field>) were extracted by regex/
  heuristic from parsed.raw_text, but that provenance wasn't kept, so
  this module re-locates each one with a best-effort raw_text.find(). A
  value found verbatim gets a real character_range/page/paragraph and
  confidence 1.0; a real but unlocatable value (e.g. a title pulled from
  the PDF's own native metadata, never repeated in the body text) gets
  confidence ~0.3 with only its own text as the snippet; an empty value
  gets confidence 0.0 — there is nothing to point to (see
  EvidenceReference's own docstring for this same 1.0/0.3/0.0 scale).

List-valued metadata (authors, keywords, affiliations) has no single
span to point to and is intentionally not covered here.
"""

from typing import Optional

from .enums import SectionType
from .interfaces import BaseTraceabilityBuilder
from .models import DocumentMetadata, DocumentStructure, EvidenceReference, ParsedDocument
from .utils import page_at_offset, paragraph_index_at, snippet_at

# Every DocumentMetadata field that holds a single located-able string
# (or int, for publication_year) — matches "metadata.<name>" traceability
# keys. Deliberately excludes list fields (see module docstring) and the
# confidence/reasoning/raw_metadata/language bookkeeping fields, which
# aren't themselves extracted facts.
_METADATA_SCALAR_FIELDS: tuple[str, ...] = (
    "title",
    "subtitle",
    "corresponding_author",
    "venue",
    "journal",
    "conference",
    "doi",
    "pmid",
    "pmcid",
    "arxiv_id",
    "clinical_trials_id",
    "publication_year",
    "publication_type",
    "abstract",
    "license",
)

# See EvidenceReference's docstring for what these two levels mean.
_UNLOCATED_CONFIDENCE = 0.3
_EMPTY_CONFIDENCE = 0.0
_LOCATED_CONFIDENCE = 1.0


class TraceabilityBuilder(BaseTraceabilityBuilder):
    """Builds one EvidenceReference per traceable fact — see module
    docstring for the two families and how each is located."""

    def build(
        self,
        parsed: ParsedDocument,
        metadata: DocumentMetadata,
        structure: DocumentStructure,
    ) -> dict[str, EvidenceReference]:
        evidence: dict[str, EvidenceReference] = {}
        evidence.update(self._build_metadata_evidence(parsed, metadata))
        evidence.update(self._build_section_evidence(parsed, structure))
        return evidence

    def _build_metadata_evidence(
        self, parsed: ParsedDocument, metadata: DocumentMetadata
    ) -> dict[str, EvidenceReference]:
        evidence: dict[str, EvidenceReference] = {}
        for field_name in _METADATA_SCALAR_FIELDS:
            value = getattr(metadata, field_name)
            text_value = str(value) if isinstance(value, int) else value
            evidence[f"metadata.{field_name}"] = self._locate(parsed, text_value)
        return evidence

    def _build_section_evidence(
        self, parsed: ParsedDocument, structure: DocumentStructure
    ) -> dict[str, EvidenceReference]:
        evidence: dict[str, EvidenceReference] = {}
        for section_type in structure.normalized_headings:
            key = self._first_key_for_type(structure, section_type)
            if key is None:
                continue
            start, end = structure.section_offsets[key]
            evidence[f"structure.section.{section_type.value}"] = EvidenceReference(
                page=page_at_offset(parsed.page_ranges, start),
                section=section_type,
                paragraph=paragraph_index_at(parsed.raw_text, start),
                character_range=(start, end),
                text_snippet=snippet_at(parsed.raw_text, start, end),
                confidence=_LOCATED_CONFIDENCE,
            )
        return evidence

    @staticmethod
    def _first_key_for_type(structure: DocumentStructure, section_type: SectionType) -> Optional[str]:
        """The first raw heading (in detection order — dict insertion
        order — since sections.py builds section_types in the same order
        it processes candidates) that normalized to `section_type` —
        representative when several headings merged into one type."""
        for key, mapped_type in structure.section_types.items():
            if mapped_type == section_type:
                return key
        return None

    @staticmethod
    def _locate(parsed: ParsedDocument, value: Optional[str]) -> EvidenceReference:
        if not value:
            return EvidenceReference(
                page=None,
                section=None,
                paragraph=None,
                character_range=None,
                text_snippet="",
                confidence=_EMPTY_CONFIDENCE,
            )

        index = parsed.raw_text.find(value)
        if index == -1:
            return EvidenceReference(
                page=None,
                section=None,
                paragraph=None,
                character_range=None,
                text_snippet=value,
                confidence=_UNLOCATED_CONFIDENCE,
            )

        end = index + len(value)
        return EvidenceReference(
            page=page_at_offset(parsed.page_ranges, index),
            section=None,
            paragraph=paragraph_index_at(parsed.raw_text, index),
            character_range=(index, end),
            text_snippet=snippet_at(parsed.raw_text, index, end),
            confidence=_LOCATED_CONFIDENCE,
        )
