"""Population and demographic extraction — sample size, age range, sex
distribution, and inclusion/exclusion criteria, searched in the sections
where a clinical paper's "Participants"/"Study Population" subsection
typically lives (abstract/methods/results).

age_range/mean_age/sex_distribution are kept as the raw matched phrase
(e.g. "18-65 years", "mean age of 42.3", "52% were female") rather than
parsed into separate numeric fields — see models.py's own module
docstring for why free text is the honest choice here.
"""

import re
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex, TextMatch
from ..entity_registry import EntityRegistry
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import DemographicData, Population

_POPULATION_SECTIONS = (SectionType.ABSTRACT, SectionType.METHODS, SectionType.RESULTS)

_SAMPLE_SIZE_RE = r"\b\d[\d,]{0,6}\s+(?:patients|participants|subjects|individuals)\b"
_AGE_RANGE_RE = r"\b\d{1,3}\s*(?:-|to|–)\s*\d{1,3}\s*years\b"
_MEAN_AGE_RE = r"(?:mean|median|average)\s+age\s*(?:of|was|:)?\s*\d{1,3}(?:\.\d+)?"
_SEX_RE = r"\d{1,3}(?:\.\d+)?\s*%\s*(?:were\s*|was\s*)?(?:female|male|women|men)"
_INCLUSION_RE = r"inclusion criteria[:\s]*[^.]*\."
_EXCLUSION_RE = r"exclusion criteria[:\s]*[^.]*\."

_PATTERN_CONFIDENCE = 0.7


class PopulationExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        sections = list(_POPULATION_SECTIONS)

        sample_match = _first_match(index, _SAMPLE_SIZE_RE, sections)
        age_match = _first_match(index, _AGE_RANGE_RE, sections)
        mean_age_match = _first_match(index, _MEAN_AGE_RE, sections)
        sex_match = _first_match(index, _SEX_RE, sections)
        inclusion = [m.matched_text for m in index.find_text(_INCLUSION_RE, sections)]
        exclusion = [m.matched_text for m in index.find_text(_EXCLUSION_RE, sections)]

        sample_size = _extract_int(sample_match.matched_text) if sample_match else None
        found_anything = sample_match or age_match or mean_age_match or sex_match or inclusion or exclusion
        confidence = _PATTERN_CONFIDENCE if found_anything else 0.0

        primary_evidence = None
        for match in (sample_match, age_match, mean_age_match, sex_match):
            if match is not None:
                primary_evidence = index.evidence_for(match, _PATTERN_CONFIDENCE)
                break

        population = Population(
            sample_size=sample_size,
            inclusion_criteria=inclusion,
            exclusion_criteria=exclusion,
            age_range=age_match.matched_text if age_match else None,
            confidence=confidence,
            evidence=primary_evidence,
        )
        demographic_data = DemographicData(
            total_participants=sample_size,
            mean_age=mean_age_match.matched_text if mean_age_match else None,
            sex_distribution=sex_match.matched_text if sex_match else None,
            confidence=confidence,
            evidence=primary_evidence,
        )

        return ExtractionResult(entities=[], populations=[population], demographic_data=demographic_data)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # Same tier as every extractor except clinical_entities.py (100)
        # — none of these read the registry, so they can run alongside
        # each other freely (see registry.py's tiered execute_parallel()).
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["populations", "demographic_data"]


def _first_match(index: DocumentIndex, pattern: str, sections: list[SectionType]) -> Optional[TextMatch]:
    matches = index.find_text(pattern, sections)
    return matches[0] if matches else None


def _extract_int(text: str) -> Optional[int]:
    digits = re.match(r"[\d,]+", text)
    return int(digits.group(0).replace(",", "")) if digits else None
