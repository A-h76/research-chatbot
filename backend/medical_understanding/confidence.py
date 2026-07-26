"""Deterministic confidence calculation — computes the four inputs
ConfidenceScore.calculate() (models.py) combines into one overall score,
from real extraction data. The formula itself lives on ConfidenceScore
since the task's own spec puts it there as a @staticmethod; this module
only computes what feeds it:

- section_quality: how much of the document's relevant structure was
  actually available to extract from — reuses
  backend.analysis_context.models.SectionProfile.section_completeness
  (Phase 1.3's own already-computed per-section completeness), not a
  new text-quality heuristic.
- evidence_count: how much evidence backs the extraction, scaled against
  a target count rather than reported raw (so 3 entities in a short
  case report isn't penalized the way 3 entities in a 40-page
  systematic review would be) — capped at 1.0.
- keyword_confidence: the mean of the individual entities' own per-match
  extraction confidence.
- normalization_quality: the fraction of entities that normalized to
  EXACT_MATCH or SYNONYM_MATCH rather than FUZZY_MATCH/AMBIGUOUS/UNKNOWN
  (see enums.EntityNormalizationStatus) — "how much of what we found do
  we actually recognize", not a black-box similarity score.
"""

from backend.document_understanding.enums import SectionType

from .enums import EntityNormalizationStatus
from .models import ClinicalEntity, ConfidenceScore

# A target entity count beyond which more evidence stops adding
# confidence — deliberately modest, since a typical clinical paper
# doesn't mention hundreds of distinct clinical concepts.
_TARGET_EVIDENCE_COUNT = 15

_GOOD_NORMALIZATION_STATUSES = frozenset(
    {EntityNormalizationStatus.EXACT_MATCH, EntityNormalizationStatus.SYNONYM_MATCH}
)


def compute_confidence(
    entities: list[ClinicalEntity],
    section_completeness: dict[SectionType, float],
) -> ConfidenceScore:
    return ConfidenceScore.calculate(
        section_quality=_section_quality(section_completeness),
        evidence_count=_evidence_count(len(entities)),
        keyword_confidence=_keyword_confidence(entities),
        normalization_quality=_normalization_quality(entities),
    )


def _section_quality(section_completeness: dict[SectionType, float]) -> float:
    if not section_completeness:
        return 0.0
    return sum(section_completeness.values()) / len(section_completeness)


def _evidence_count(count: int) -> float:
    return min(count / _TARGET_EVIDENCE_COUNT, 1.0)


def _keyword_confidence(entities: list[ClinicalEntity]) -> float:
    if not entities:
        return 0.0
    return sum(entity.confidence for entity in entities) / len(entities)


def _normalization_quality(entities: list[ClinicalEntity]) -> float:
    if not entities:
        return 0.0
    good = sum(1 for entity in entities if entity.normalization_status in _GOOD_NORMALIZATION_STATUSES)
    return good / len(entities)
