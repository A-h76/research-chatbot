"""Multi-dimensional document quality assessment.

Composes backend.processing.quality.QualityAssessor (see package
docstring's reuse table) for ocr_quality/extraction_quality and the base
warnings/errors — both reused verbatim, since their signals (page-text
ratio, garbled-character ratio, words-per-page) don't depend on anything
this package computes differently. Adds three new dimensions the legacy
assessor has no equivalent for: metadata_quality (field coverage),
section_quality (core-section coverage + detector confidence), and
layout_quality (how much structure came from a strong pattern —
markdown/numbered/underline — vs. the weaker bare-line heuristic).
"""

from backend.processing.quality import QualityAssessor as _LegacyQualityAssessor

from .enums import HeadingType, SectionType
from .interfaces import BaseQualityAssessor
from .models import DocumentMetadata, DocumentQuality, DocumentStatistics, DocumentStructure, ParsedDocument
from .utils import to_legacy_parsed, to_legacy_sections

# Fields whose presence is meaningful evidence of good metadata
# extraction — the same "core" fields backend.processing's own
# MetadataExtractor has always populated, not the newer best-effort
# identifiers (PMID/arXiv/etc.), which are legitimately absent from most
# papers and would only dilute this signal.
_METADATA_QUALITY_FIELDS: tuple[str, ...] = (
    "title",
    "authors",
    "venue",
    "doi",
    "publication_year",
    "abstract",
    "keywords",
)

# Same baseline backend.processing.quality uses for missing_sections.
_EXPECTED_CORE_SECTION_TYPES: tuple[SectionType, ...] = (
    SectionType.ABSTRACT,
    SectionType.METHODS,
    SectionType.RESULTS,
    SectionType.DISCUSSION,
)

_STRONG_HEADING_TYPES = frozenset({HeadingType.MARKDOWN, HeadingType.NUMBERED, HeadingType.UNDERLINE})


class QualityAssessor(BaseQualityAssessor):
    """Assesses a fully-parsed, structured document across five
    dimensions — see DocumentQuality's own docstring for what each one
    means."""

    def __init__(self) -> None:
        self._legacy = _LegacyQualityAssessor()

    def assess(
        self,
        parsed: ParsedDocument,
        metadata: DocumentMetadata,
        structure: DocumentStructure,
        statistics: DocumentStatistics,
    ) -> DocumentQuality:
        legacy = self._legacy.assess(to_legacy_parsed(parsed), to_legacy_sections(structure))

        metadata_quality = self._assess_metadata_quality(metadata)
        section_quality = self._assess_section_quality(structure)
        layout_quality = self._assess_layout_quality(structure)
        completeness = (metadata_quality + section_quality) / 2

        confidence = (
            legacy.ocr_quality + legacy.text_extraction_quality + metadata_quality + section_quality + layout_quality
        ) / 5

        return DocumentQuality(
            ocr_quality=legacy.ocr_quality,
            extraction_quality=legacy.text_extraction_quality,
            metadata_quality=metadata_quality,
            section_quality=section_quality,
            layout_quality=layout_quality,
            completeness=completeness,
            confidence=confidence,
            warnings=list(legacy.warnings),
            errors=list(legacy.errors),
        )

    @staticmethod
    def _assess_metadata_quality(metadata: DocumentMetadata) -> float:
        populated = sum(1 for name in _METADATA_QUALITY_FIELDS if getattr(metadata, name))
        return populated / len(_METADATA_QUALITY_FIELDS)

    @staticmethod
    def _assess_section_quality(structure: DocumentStructure) -> float:
        if not structure.heading_order:
            return 0.0
        present = sum(
            1 for section_type in _EXPECTED_CORE_SECTION_TYPES if section_type in structure.normalized_headings
        )
        core_section_ratio = present / len(_EXPECTED_CORE_SECTION_TYPES)
        return (structure.confidence + core_section_ratio) / 2

    @staticmethod
    def _assess_layout_quality(structure: DocumentStructure) -> float:
        if not structure.heading_types:
            return 0.0
        strong = sum(1 for heading_type in structure.heading_types.values() if heading_type in _STRONG_HEADING_TYPES)
        return strong / len(structure.heading_types)
