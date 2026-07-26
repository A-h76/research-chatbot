"""Comparator extraction — what an intervention was compared against
(placebo, standard/usual care, an active comparator, or an explicit
"compared to X"/"versus X" phrase), searched in methods/abstract.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex
from ..entity_registry import EntityRegistry
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import Comparator

_COMPARATOR_SECTIONS = (SectionType.METHODS, SectionType.ABSTRACT)

_PLACEBO_RE = r"\bplacebo\b"
_STANDARD_CARE_RE = r"\b(?:standard|usual)\s+(?:care|treatment)\b"
_ACTIVE_CONTROL_RE = r"\bactive\s+(?:control|comparator)\b"
_VERSUS_RE = r"\b(?:compared (?:to|with)|versus|vs\.?)\s+[A-Za-z][\w\s-]{2,40}"

_CONFIDENCE = 0.7


class ComparatorExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        sections = list(_COMPARATOR_SECTIONS)
        comparators: list[Comparator] = []

        placebo_matches = index.find_text(_PLACEBO_RE, sections)
        if placebo_matches:
            comparators.append(
                Comparator(
                    name="placebo",
                    is_placebo=True,
                    confidence=_CONFIDENCE,
                    evidence=index.evidence_for(placebo_matches[0], _CONFIDENCE),
                )
            )

        standard_matches = index.find_text(_STANDARD_CARE_RE, sections)
        if standard_matches:
            comparators.append(
                Comparator(
                    name=standard_matches[0].matched_text,
                    confidence=_CONFIDENCE,
                    evidence=index.evidence_for(standard_matches[0], _CONFIDENCE),
                )
            )

        active_matches = index.find_text(_ACTIVE_CONTROL_RE, sections)
        if active_matches:
            comparators.append(
                Comparator(
                    name=active_matches[0].matched_text,
                    is_active_control=True,
                    confidence=_CONFIDENCE,
                    evidence=index.evidence_for(active_matches[0], _CONFIDENCE),
                )
            )

        for match in index.find_text(_VERSUS_RE, sections):
            comparators.append(
                Comparator(
                    name=match.matched_text, confidence=_CONFIDENCE, evidence=index.evidence_for(match, _CONFIDENCE)
                )
            )

        return ExtractionResult(entities=[], comparators=comparators)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # See populations.py's identical priority() docstring.
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["comparators"]
