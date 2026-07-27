"""Statistical measure extraction — p-values, confidence intervals,
hazard/odds/relative risk ratios, mean differences, standard deviations,
and effect sizes, searched across abstract/results/discussion (where a
paper's quantitative findings are reported).
"""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType

from ..document_index import DocumentIndex
from ..entity_registry import EntityRegistry
from ..enums import StatisticalMeasureType
from ..interfaces import BaseExtractor, ExtractionResult
from ..models import StatisticalMeasure

_SECTIONS = (SectionType.ABSTRACT, SectionType.RESULTS, SectionType.DISCUSSION)

_MEASURE_PATTERNS: dict[StatisticalMeasureType, str] = {
    StatisticalMeasureType.P_VALUE: r"\bp\s*[<>=]\s*0?\.\d+\b",
    StatisticalMeasureType.CONFIDENCE_INTERVAL: r"95%\s*CI[:\s]*[\d.\-–,\s]+",
    StatisticalMeasureType.HAZARD_RATIO: r"\b(?:HR|hazard ratio)\s*[:=]?\s*\d+\.\d+",
    StatisticalMeasureType.ODDS_RATIO: r"\b(?:OR|odds ratio)\s*[:=]?\s*\d+\.\d+",
    StatisticalMeasureType.RELATIVE_RISK: r"\b(?:RR|relative risk)\s*[:=]?\s*\d+\.\d+",
    StatisticalMeasureType.MEAN_DIFFERENCE: r"mean difference[^.]{0,60}",
    StatisticalMeasureType.STANDARD_DEVIATION: r"(?:\bSD\s*[:=]?\s*\d+\.\d+|±\s*\d+\.\d+)",
    StatisticalMeasureType.EFFECT_SIZE: r"effect size[^.]{0,60}",
}

# Numeric statistical patterns (p<0.05, HR=1.4, ...) are fairly
# unambiguous once matched — higher than the plain-keyword confidence
# used elsewhere in this package.
_CONFIDENCE = 0.75


class StatisticalMeasuresExtractor(BaseExtractor):
    """See module docstring."""

    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        sections = list(_SECTIONS)
        measures = [
            StatisticalMeasure(
                measure_type=measure_type,
                value=match.matched_text.strip(),
                confidence=_CONFIDENCE,
                evidence=index.evidence_for(match, _CONFIDENCE),
            )
            for measure_type, pattern in _MEASURE_PATTERNS.items()
            for match in index.find_text(pattern, sections)
        ]
        return ExtractionResult(entities=[], statistical_measures=measures)

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        # See extractors/populations.py's identical priority() docstring.
        return 50

    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> list[str]:
        return ["statistical_measures"]
