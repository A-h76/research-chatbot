"""Temporal data extraction — study duration, follow-up period,
enrollment period, and key timepoints (e.g. "at 12 weeks"), searched
across methods/results/discussion.
"""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex, TextMatch
from ..entity_registry import EntityRegistry
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import TemporalData

_SECTIONS = (SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION)

_DURATION_RE = r"(?:study|trial)\s+(?:duration|period)\s+of\s+\d+\s+(?:days|weeks|months|years)"
_FOLLOW_UP_RE = r"follow(?:ed)?[\s-]up\s+(?:period\s+of\s+|for\s+)?\d+\s+(?:days|weeks|months|years)"
_ENROLLMENT_RE = r"enroll(?:ed|ment)[^.]{0,80}(?:between|from)[^.]{0,60}"
_TIMEPOINT_RE = r"\bat\s+\d+\s+(?:days|weeks|months|years)\b"

_CONFIDENCE = 0.7


class TemporalDataExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        sections = list(_SECTIONS)

        duration_match = _first(index, _DURATION_RE, sections)
        follow_up_match = _first(index, _FOLLOW_UP_RE, sections)
        enrollment_match = _first(index, _ENROLLMENT_RE, sections)
        timepoint_matches = index.find_text(_TIMEPOINT_RE, sections)

        evidence = [
            index.evidence_for(match, _CONFIDENCE)
            for match in (duration_match, follow_up_match, enrollment_match)
            if match is not None
        ]
        evidence.extend(index.evidence_for(match, _CONFIDENCE) for match in timepoint_matches)

        temporal_data = TemporalData(
            study_duration=duration_match.matched_text if duration_match else None,
            follow_up_period=follow_up_match.matched_text if follow_up_match else None,
            enrollment_period=enrollment_match.matched_text.strip() if enrollment_match else None,
            key_timepoints=sorted({match.matched_text for match in timepoint_matches}),
            confidence=_CONFIDENCE if evidence else 0.0,
            evidence=evidence,
        )
        return ExtractionResult(entities=[], temporal_data=temporal_data)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # See extractors/populations.py's identical priority() docstring.
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["temporal_data"]


def _first(index: DocumentIndex, pattern: str, sections: list[SectionType]) -> Optional[TextMatch]:
    matches = index.find_text(pattern, sections)
    return matches[0] if matches else None
