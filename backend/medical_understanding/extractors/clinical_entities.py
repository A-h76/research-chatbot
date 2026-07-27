"""Clinical entity extraction — finds mentions of medical conditions,
drugs, procedures, symptoms, lab tests, and adverse events across the
document's clinically-relevant sections (abstract/introduction/methods/
results/discussion — not references/acknowledgments/appendix), using a
small, curated keyword table per ClinicalEntityType. Deliberately not
exhaustive medical vocabulary and not a real UMLS/SNOMED CT lookup — see
config.py's and normalizers.py's own docstrings for why; new terms are
recognized by extending _KEYWORDS_BY_TYPE below, the same "add a dict
entry, no logic changes" pattern backend.classification.pass2.keywords
already establishes.

The first mention of each distinct (canonical value, entity_type) pair
becomes the one ClinicalEntity in this extractor's own result — later
mentions of the same concept are still found by find_text() but
EntityRegistry.register_entity() dedupes them to the already-registered
entity (see entity_registry.py), so this list is "one entity per
distinct concept actually present", not "one row per literal mention".
"""

import re

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex
from ..entity_registry import EntityRegistry
from ..enums import ClinicalEntityType
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import ClinicalEntity
from ..normalizers import normalize

_SEARCHABLE_SECTIONS = (
    SectionType.ABSTRACT,
    SectionType.INTRODUCTION,
    SectionType.METHODS,
    SectionType.RESULTS,
    SectionType.DISCUSSION,
)

_KEYWORDS_BY_TYPE: dict[ClinicalEntityType, tuple[str, ...]] = {
    ClinicalEntityType.CONDITION: (
        "diabetes",
        "hypertension",
        "myocardial infarction",
        "stroke",
        "cancer",
        "asthma",
        "copd",
        "heart failure",
        "depression",
        "obesity",
        "arthritis",
        "chronic kidney disease",
    ),
    ClinicalEntityType.DRUG: (
        "aspirin",
        "metformin",
        "insulin",
        "warfarin",
        "statin",
        "placebo",
        "ibuprofen",
        "acetaminophen",
        "antibiotic",
        "corticosteroid",
        "beta-blocker",
        "ace inhibitor",
    ),
    ClinicalEntityType.PROCEDURE: (
        "surgery",
        "biopsy",
        "catheterization",
        "angioplasty",
        "dialysis",
        "chemotherapy",
        "radiotherapy",
        "transplant",
        "endoscopy",
        "intubation",
    ),
    ClinicalEntityType.SYMPTOM: (
        "fatigue",
        "nausea",
        "dyspnea",
        "headache",
        "dizziness",
        "vomiting",
        "shortness of breath",
    ),
    ClinicalEntityType.LAB_TEST: (
        "hba1c",
        "cholesterol",
        "creatinine",
        "hemoglobin",
        "blood pressure",
        "blood glucose",
        "white blood cell count",
        "c-reactive protein",
        "ejection fraction",
    ),
    ClinicalEntityType.ADVERSE_EVENT: (
        "adverse event",
        "serious adverse event",
        "side effect",
        "toxicity",
    ),
}

# A literal keyword match is a moderate, not high, confidence signal —
# it's evidence a concept was mentioned, not proof of its clinical role
# (matches backend.classification.pass2's own "a body-text keyword is a
# weaker signal than a structural/venue match" calibration).
_KEYWORD_CONFIDENCE = 0.7


class ClinicalEntityExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        entities: list[ClinicalEntity] = []
        for entity_type, keywords in _KEYWORDS_BY_TYPE.items():
            for keyword in keywords:
                matches = index.find_text(re.escape(keyword), list(_SEARCHABLE_SECTIONS))
                if not matches:
                    continue

                canonical, status, synonyms = normalize(keyword)
                match = matches[0]
                entity = ClinicalEntity(
                    value=canonical,
                    entity_type=entity_type,
                    raw_text=match.matched_text,
                    normalization_status=status,
                    confidence=_KEYWORD_CONFIDENCE,
                    evidence=index.evidence_for(match, _KEYWORD_CONFIDENCE),
                    synonyms=synonyms,
                )
                registered = registry.register_entity(entity)
                if registered is entity:
                    entities.append(entity)

        return ExtractionResult(entities=entities)

    def supports(self, context: AnalysisContext) -> bool:
        # The pipeline's own routing check already gated on medical/
        # clinical before any extractor runs (see pipeline.py) — every
        # medical document is worth trying to find clinical entities in,
        # so this is unconditionally True. A future narrower condition
        # is a one-line change here, not a redesign.
        return True

    def priority(self) -> int:
        return 100

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["clinical_entities"]
