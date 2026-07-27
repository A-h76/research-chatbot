"""Section completeness assessment — reuses Phase 1.1's already-computed
DocumentStructure (normalized_headings/heading_types/section_types) and
Phase 1.2's already-built DOCUMENT_TYPE_STRUCTURAL_FEATURES mapping
(which sections a given DocumentType is expected to have) rather than
building a third, parallel "expected sections per type" table.
"""

from backend.classification.pass2.keywords import DOCUMENT_TYPE_STRUCTURAL_FEATURES
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import HeadingType, SectionType
from backend.document_understanding.models import DocumentStructure, EvidenceReference, ProcessedDocument

from .interfaces import BaseSectionProfiler
from .models import SectionProfile

_STRONG_HEADING_TYPES = frozenset({HeadingType.MARKDOWN, HeadingType.NUMBERED, HeadingType.UNDERLINE})

# A section detected via a strong structural pattern (markdown/numbered/
# underline) is more trustworthy than one only matched by the weaker
# bare-line heuristic (see backend.document_understanding.headings).
_STRONG_SECTION_CONFIDENCE = 1.0
_WEAK_SECTION_CONFIDENCE = 0.6

# A present section with fewer words than this reads as a stub (e.g. a
# one-line placeholder), not genuinely complete content.
_MIN_WORDS_FOR_FULL_COMPLETENESS = 20
_FULL_COMPLETENESS = 1.0
_THIN_COMPLETENESS = 0.5
_MISSING_COMPLETENESS = 0.0


class SectionProfiler(BaseSectionProfiler):
    """Builds a SectionProfile from a ProcessedDocument's already-
    detected structure, scoped to what's recommended for the document's
    already-classified type."""

    def profile(self, document: ProcessedDocument, classification: ClassificationResult) -> SectionProfile:
        structure = document.structure
        present = list(structure.normalized_headings)
        recommended = list(DOCUMENT_TYPE_STRUCTURAL_FEATURES.get(classification.document_type.label, ()))
        missing = [section_type for section_type in recommended if section_type not in structure.normalized_headings]

        tracked_sections = set(present) | set(recommended)
        section_completeness = {
            section_type: _completeness(structure, section_type) for section_type in tracked_sections
        }
        section_confidence = {section_type: _confidence(structure, section_type) for section_type in present}

        return SectionProfile(
            present_sections=present,
            missing_sections=missing,
            section_completeness=section_completeness,
            section_confidence=section_confidence,
            recommended_sections=recommended,
            evidence=_evidence(document, present),
        )


def _completeness(structure: DocumentStructure, section_type: SectionType) -> float:
    content = structure.normalized_headings.get(section_type)
    if content is None:
        return _MISSING_COMPLETENESS
    if len(content.split()) >= _MIN_WORDS_FOR_FULL_COMPLETENESS:
        return _FULL_COMPLETENESS
    return _THIN_COMPLETENESS


def _confidence(structure: DocumentStructure, section_type: SectionType) -> float:
    contributing_keys = [key for key, mapped_type in structure.section_types.items() if mapped_type == section_type]
    if any(structure.heading_types.get(key) in _STRONG_HEADING_TYPES for key in contributing_keys):
        return _STRONG_SECTION_CONFIDENCE
    return _WEAK_SECTION_CONFIDENCE


def _evidence(document: ProcessedDocument, present_sections: list[SectionType]) -> list[EvidenceReference]:
    evidence = []
    for section_type in present_sections:
        key = f"structure.section.{section_type.value}"
        if key in document.traceability:
            evidence.append(document.traceability[key])
    return evidence
