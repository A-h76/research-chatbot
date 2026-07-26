"""MedicalUnderstandingPipeline — the package's one public entry point.

    (ProcessedDocument, ClassificationResult, AnalysisContext)
        |
        v
    Routing check         (_should_run)          -- skip entirely if not medical/clinical
        |
        v
    DocumentIndex          (document_index.py)     -- built once, shared by every extractor
        |
        v
    ExtractorRegistry       (registry.py)           -- filters via supports(), runs in parallel
        |
        v
    Post-Processor          (post_processor.py)     -- normalize/dedup/relate/validate
        |
        v
    PICOBuilder              (pico_builder.py)
    ConfidenceEngine          (confidence.py)
        |
        v
    MedicalUnderstanding       (models.py)

Graceful degradation, three layers deep (matching every prior phase's
own two-layer design, extended by one layer here since this phase has
more moving parts): each extractor's own crash is isolated by
ExtractorRegistry._safe_extract() (registry.py); document-index
construction, post-processing, and confidence computation are each
wrapped by this module's own _run_stage(), substituting an empty default
and a warning rather than raising; process() itself only raises for the
one caller-bug case (wrong argument types — see validators.py).
"""

import time
from typing import Callable, Optional, TypeVar

from backend.analysis_context.enums import RoutingDecision
from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .confidence import compute_confidence
from .config import MedicalUnderstandingConfig
from .document_index import DocumentIndex, build_document_index
from .entity_registry import EntityRegistry
from .extractors.clinical_entities import ClinicalEntityExtractor
from .extractors.comparators import ComparatorExtractor
from .extractors.interventions import InterventionExtractor
from .extractors.outcomes import OutcomeExtractor
from .extractors.populations import PopulationExtractor
from .extractors.statistical_measures import StatisticalMeasuresExtractor
from .extractors.study_characteristics import StudyCharacteristicsExtractor
from .extractors.temporal_data import TemporalDataExtractor
from .interfaces import ExtractionResult
from .models import ConfidenceScore, ExtractionError, ExtractionSummary, MedicalUnderstanding
from .pico_builder import build_pico
from .post_processor import PostProcessedResults, post_process
from .registry import ExtractorRegistry
from .security.regex_guard import RegexGuard
from .validators import require_valid_inputs, validate_inputs, validate_output

PIPELINE_VERSION = "1.0.0"

_MEDICAL_ROUTING_DECISIONS = frozenset(
    {
        RoutingDecision.MEDICAL_FULL,
        RoutingDecision.MEDICAL_SCOPED,
        RoutingDecision.CLINICAL_TRIAL,
        RoutingDecision.SYSTEMATIC_REVIEW,
    }
)

# Extraction result keys this pipeline merges across every extractor's
# ExtractionResult.extras — see _merge_results().
_LIST_KEYS = ("populations", "interventions", "comparators", "outcomes", "statistical_measures", "key_findings")
_SINGLE_KEYS = ("demographic_data", "study_characteristics", "temporal_data")

_Result = TypeVar("_Result")


class MedicalUnderstandingPipeline:
    """See module docstring. config controls which extractors are
    enabled, resource limits, and parallel execution — see config.py."""

    def __init__(self, config: Optional[MedicalUnderstandingConfig] = None) -> None:
        self.config = config or MedicalUnderstandingConfig()
        self.registry = ExtractorRegistry(self.config)
        self._register_default_extractors()

    def _register_default_extractors(self) -> None:
        self.registry.register("clinical_entities", ClinicalEntityExtractor())
        self.registry.register("populations", PopulationExtractor())
        self.registry.register("interventions", InterventionExtractor())
        self.registry.register("comparators", ComparatorExtractor())
        self.registry.register("outcomes", OutcomeExtractor())
        self.registry.register("study_characteristics", StudyCharacteristicsExtractor())
        self.registry.register("statistical_measures", StatisticalMeasuresExtractor())
        self.registry.register("temporal_data", TemporalDataExtractor())

    def process(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
    ) -> MedicalUnderstanding:
        require_valid_inputs(document, classification, context)
        start = time.perf_counter()

        if not self._should_run(context):
            return MedicalUnderstanding(
                skipped=True,
                reasoning=f"document not medical/clinical (routing: {context.routing_profile.primary_routing.value})",
                pipeline_version=PIPELINE_VERSION,
                processing_time_ms=(time.perf_counter() - start) * 1000,
            )

        warnings = validate_inputs(document, classification, context)

        doc_index = self._run_stage(
            "document_index", lambda: build_document_index(document, self._regex_guard()), DocumentIndex(), warnings
        )

        entity_registry = EntityRegistry()
        enabled = self.registry.get_enabled(context)
        results = self.registry.execute_parallel(enabled, doc_index, classification, context, entity_registry)

        merged, extractor_errors, extractor_recoveries, extractor_warnings = self._merge_results(results)
        warnings.extend(extractor_warnings)

        processed = self._run_stage(
            "post_processing",
            lambda: post_process(entity_registry, merged, self.config),
            PostProcessedResults(),
            warnings,
        )
        warnings.extend(processed.warnings)

        confidence = self._run_stage(
            "confidence",
            lambda: compute_confidence(processed.clinical_entities, context.section_profile.section_completeness),
            ConfidenceScore.empty(),
            warnings,
        )

        pico_elements = build_pico(
            processed.populations, processed.interventions, processed.comparators, processed.outcomes
        )
        summary = self._build_summary(enabled, results, processed)

        understanding = MedicalUnderstanding(
            skipped=False,
            reasoning=None,
            clinical_entities=processed.clinical_entities,
            pico_elements=pico_elements,
            study_characteristics=merged.get("study_characteristics"),
            interventions=processed.interventions,
            populations=processed.populations,
            comparators=processed.comparators,
            outcomes=processed.outcomes,
            statistical_measures=processed.statistical_measures,
            temporal_data=merged.get("temporal_data"),
            demographic_data=merged.get("demographic_data"),
            key_findings=processed.key_findings,
            extraction_summary=summary,
            confidence=confidence,
            errors=extractor_errors,
            warnings=warnings,
            recoveries=extractor_recoveries,
            processing_time_ms=(time.perf_counter() - start) * 1000,
            pipeline_version=PIPELINE_VERSION,
        )

        understanding.warnings.extend(validate_output(understanding, self.config))
        return understanding

    def _should_run(self, context: AnalysisContext) -> bool:
        return context.routing_profile.primary_routing in _MEDICAL_ROUTING_DECISIONS

    def _regex_guard(self) -> RegexGuard:
        return RegexGuard(timeout_ms=self.config.regex_timeout_ms, max_pattern_length=self.config.max_regex_length)

    @staticmethod
    def _merge_results(
        results: dict[str, ExtractionResult],
    ) -> tuple[dict, list[ExtractionError], list, list[str]]:
        merged: dict = {key: [] for key in _LIST_KEYS}
        for single_key in _SINGLE_KEYS:
            merged[single_key] = None

        errors: list[ExtractionError] = []
        recoveries: list = []
        warnings: list[str] = []

        for result in results.values():
            errors.extend(result.errors)
            recoveries.extend(result.recoveries)
            warnings.extend(result.warnings)
            for key in _LIST_KEYS:
                merged[key].extend(result.get(key) or [])
            for key in _SINGLE_KEYS:
                if merged[key] is None:
                    merged[key] = result.get(key)

        return merged, errors, recoveries, warnings

    @staticmethod
    def _build_summary(
        enabled: list, results: dict[str, ExtractionResult], processed: PostProcessedResults
    ) -> ExtractionSummary:
        executed = list(results.keys())
        failed = [name for name, result in results.items() if result.errors]
        enabled_names = [name for name, _ in enabled]

        entity_counts: dict[str, int] = {"clinical_entities": len(processed.clinical_entities)}
        for key in ("populations", "interventions", "comparators", "outcomes", "statistical_measures", "key_findings"):
            entity_counts[key] = len(getattr(processed, key))
        total_entities = sum(entity_counts.values())

        success_count = len(executed) - len(failed)
        success_rate = success_count / len(executed) if executed else 0.0

        return ExtractionSummary(
            enabled_extractors=enabled_names,
            executed_extractors=executed,
            skipped_extractors=[],
            failed_extractors=failed,
            entity_counts=entity_counts,
            total_entities=total_entities,
            partial_success=0 < len(failed) < len(executed),
            overall_success_rate=success_rate,
        )

    @staticmethod
    def _run_stage(name: str, fn: Callable[[], _Result], default: _Result, warnings: list[str]) -> _Result:
        """The one graceful-degradation boundary for whole-stage calls
        (see module docstring) — catches any exception `fn` raises,
        substituting a neutral default so the rest of process() is
        unaffected."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- intentional catch-all, see docstring above
            warnings.append(f"{name} stage failed: {exc}")
            return default
