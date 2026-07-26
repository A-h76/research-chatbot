"""Study characteristics extraction — blinding, randomization method,
number of arms/sites, and multi-center status, layered on top of
classification's already-decided study_design (reused directly, not
re-derived — see backend.classification.pass2.enums.StudyDesign).
"""

import re
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex, TextMatch
from ..entity_registry import EntityRegistry
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import StudyCharacteristics

_SECTIONS = (SectionType.METHODS, SectionType.ABSTRACT)

_BLINDING_RE = r"\b(?:double|single|triple)[\s-]blind(?:ed)?\b|\bopen[\s-]label\b"
_RANDOMIZATION_RE = r"\brandom(?:ly|i[sz]ation)[\w\s]{0,40}"
_ARMS_RE = r"\b\d+[\s-]arm(?:ed)?\b"
_MULTICENTER_RE = r"\bmulti[\s-]?cent(?:er|re)\b"
_SITES_RE = r"\b\d+\s+(?:sites|centers|centres)\b"

_CONFIDENCE = 0.7


class StudyCharacteristicsExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        sections = list(_SECTIONS)

        blinding_match = _first(index, _BLINDING_RE, sections)
        randomization_match = _first(index, _RANDOMIZATION_RE, sections)
        arms_match = _first(index, _ARMS_RE, sections)
        multicenter_matches = index.find_text(_MULTICENTER_RE, sections)
        sites_match = _first(index, _SITES_RE, sections)

        evidence = [
            index.evidence_for(match, _CONFIDENCE)
            for match in (blinding_match, randomization_match, arms_match, sites_match)
            if match is not None
        ]
        if multicenter_matches:
            evidence.append(index.evidence_for(multicenter_matches[0], _CONFIDENCE))

        study_characteristics = StudyCharacteristics(
            study_design=classification.study_design.label,
            number_of_arms=_extract_int(arms_match.matched_text) if arms_match else None,
            blinding=blinding_match.matched_text if blinding_match else None,
            randomization_method=randomization_match.matched_text.strip() if randomization_match else None,
            multicenter=True if multicenter_matches else None,
            number_of_sites=_extract_int(sites_match.matched_text) if sites_match else None,
            confidence=_CONFIDENCE if evidence else classification.study_design.confidence,
            evidence=evidence,
        )
        return ExtractionResult(entities=[], study_characteristics=study_characteristics)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # See extractors/populations.py's identical priority() docstring.
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["study_characteristics"]


def _first(index: DocumentIndex, pattern: str, sections: list[SectionType]) -> Optional[TextMatch]:
    matches = index.find_text(pattern, sections)
    return matches[0] if matches else None


def _extract_int(text: str) -> Optional[int]:
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None
