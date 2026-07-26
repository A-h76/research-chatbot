"""Outcome and key-finding extraction — primary/secondary/safety
endpoints (searched via their standard clinical-trial labels, usually
defined in methods/abstract) plus notable result statements (sentences
reporting statistical significance, searched in results/discussion).
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex
from ..entity_registry import EntityRegistry
from ..enums import OutcomeType
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import KeyFinding, Outcome

_OUTCOME_DEFINITION_SECTIONS = (SectionType.METHODS, SectionType.ABSTRACT)
_FINDING_SECTIONS = (SectionType.RESULTS, SectionType.DISCUSSION)

_OUTCOME_PATTERNS: dict[OutcomeType, str] = {
    OutcomeType.PRIMARY: r"primary\s+(?:outcome|endpoint)(?:\s+was|\s*:)?\s*[^.]{0,120}",
    OutcomeType.SECONDARY: r"secondary\s+(?:outcome|endpoint)s?(?:\s+(?:was|were)|\s*:)?\s*[^.]{0,120}",
    OutcomeType.SAFETY: r"safety\s+(?:outcome|endpoint)s?(?:\s+(?:was|were)|\s*:)?\s*[^.]{0,120}",
}

_KEY_FINDING_RE = r"[^.]*significant(?:ly)?[^.]*\."

_CONFIDENCE = 0.7


class OutcomeExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        definition_sections = list(_OUTCOME_DEFINITION_SECTIONS)
        outcomes: list[Outcome] = []
        for outcome_type, pattern in _OUTCOME_PATTERNS.items():
            for match in index.find_text(pattern, definition_sections):
                outcomes.append(
                    Outcome(
                        name=match.matched_text.strip(),
                        outcome_type=outcome_type,
                        confidence=_CONFIDENCE,
                        evidence=index.evidence_for(match, _CONFIDENCE),
                    )
                )

        key_findings = [
            KeyFinding(
                statement=match.matched_text.strip(),
                confidence=_CONFIDENCE,
                evidence=index.evidence_for(match, _CONFIDENCE),
            )
            for match in index.find_text(_KEY_FINDING_RE, list(_FINDING_SECTIONS))
        ]

        return ExtractionResult(entities=[], outcomes=outcomes, key_findings=key_findings)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # See populations.py's identical priority() docstring.
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["outcomes", "key_findings"]
