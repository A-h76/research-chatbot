"""Intervention extraction — promotes already-registered DRUG/PROCEDURE
ClinicalEntity mentions (see clinical_entities.py, which must run first —
see priority()) to Intervention records when they appear near a methods-
section phrase indicating active administration ("treated with",
"administered", "received", "randomized to"), rather than a passing
mention elsewhere in the paper. Reuses clinical_entities.py's own
registered entities via EntityRegistry.entities_by_type() instead of
re-scanning the document for drug/procedure names a second time.
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex
from ..entity_registry import EntityRegistry
from ..enums import ClinicalEntityType, InterventionType
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import Intervention

_INTERVENTION_MARKER_RE = (
    r"(?:treated with|administered|received|randomi[sz]ed to|randomly assigned to(?:\s+receive)?)\s+"
    r"[A-Za-z][\w\s-]{2,40}"
)
_INTERVENTION_SECTIONS = (SectionType.METHODS, SectionType.ABSTRACT, SectionType.RESULTS)

_INTERVENTION_TYPE_BY_ENTITY_TYPE = {
    ClinicalEntityType.DRUG: InterventionType.DRUG,
    ClinicalEntityType.PROCEDURE: InterventionType.PROCEDURE,
}

_CONFIDENCE = 0.7


class InterventionExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        marker_matches = index.find_text(_INTERVENTION_MARKER_RE, list(_INTERVENTION_SECTIONS))
        candidates = registry.entities_by_type(ClinicalEntityType.DRUG) + registry.entities_by_type(
            ClinicalEntityType.PROCEDURE
        )

        interventions: list[Intervention] = []
        seen_names: set[str] = set()
        for match in marker_matches:
            lowered_marker = match.matched_text.lower()
            for entity in candidates:
                if entity.value in seen_names:
                    continue
                if entity.value in lowered_marker or entity.raw_text.lower() in lowered_marker:
                    seen_names.add(entity.value)
                    interventions.append(
                        Intervention(
                            name=entity.value,
                            intervention_type=_INTERVENTION_TYPE_BY_ENTITY_TYPE[entity.entity_type],
                            confidence=_CONFIDENCE,
                            evidence=index.evidence_for(match, _CONFIDENCE),
                        )
                    )

        return ExtractionResult(entities=[], interventions=interventions)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # Below clinical_entities.py (100) — registry.py's tiered
        # execute_parallel() guarantees clinical_entities.py's whole
        # priority tier finishes (and has registered its DRUG/PROCEDURE
        # entities) before this tier starts, so entities_by_type() above
        # never races an in-progress registration.
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["interventions"]
