"""Extractor registry — plugin-style discovery, filtering, and parallel
execution of BaseExtractor implementations.

execute_parallel() runs extractors in priority TIERS, not one flat
parallel batch: every extractor sharing the same priority() value runs
concurrently on a real thread pool, but a whole tier's futures are
resolved before the next (strictly lower-priority) tier is even
submitted. This is what actually makes "higher priority runs first" (the
interface's own words — see interfaces.py) a real guarantee rather than
a sort that gets thrown away the moment true concurrency starts:
interventions.py depends on clinical_entities.py having already
registered its DRUG/PROCEDURE entities (see interventions.py's own
module docstring), so submitting every enabled extractor to the pool at
once — as a flat, single-batch design would — could let interventions.py
run before clinical_entities.py has written anything, silently finding
nothing. EntityRegistry itself is also lock-protected (see
entity_registry.py's own module docstring) for whatever concurrent
reads/writes still happen *within* one tier.

Given Python's GIL, this buys little real speedup for CPU-bound regex
extraction — it's structurally correct (a genuine ThreadPoolExecutor
path, not a fake one), not a demonstrated performance win; every
extractor already runs in single-digit milliseconds sequentially (see
benchmark.py).
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult

from .config import MedicalUnderstandingConfig
from .document_index import DocumentIndex
from .entity_registry import EntityRegistry
from .enums import ErrorSeverity, ErrorType
from .interfaces import BaseExtractor, ExtractionResult
from .models import ExtractionError


class ExtractorRegistry:
    """Registry for discoverable extractors."""

    def __init__(self, config: Optional[MedicalUnderstandingConfig] = None) -> None:
        self._extractors: dict[str, BaseExtractor] = {}
        self._config = config or MedicalUnderstandingConfig()

    def register(self, name: str, extractor: BaseExtractor) -> None:
        self._extractors[name] = extractor

    def unregister(self, name: str) -> None:
        self._extractors.pop(name, None)

    def get_enabled(self, context: AnalysisContext) -> list[tuple[str, BaseExtractor]]:
        """Every registered extractor that's both named in config.
        enabled_extractors and whose own supports(context) agrees —
        sorted by priority() descending (higher runs first)."""
        enabled = [
            (name, extractor)
            for name, extractor in self._extractors.items()
            if name in self._config.enabled_extractors and extractor.supports(context)
        ]
        return sorted(enabled, key=lambda pair: pair[1].priority(), reverse=True)

    def execute_parallel(
        self,
        enabled: list[tuple[str, BaseExtractor]],
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> dict[str, ExtractionResult]:
        """Runs every (name, extractor) in `enabled` in descending-
        priority tiers (see module docstring) — within a tier, in
        parallel via a thread pool if config.enable_parallel, sequentially
        otherwise. A raising extractor never takes down the others: its
        ExtractionResult becomes an empty one carrying the caught error
        (see _safe_extract())."""
        results: dict[str, ExtractionResult] = {}
        for tier in self._tiers(enabled):
            if not self._config.enable_parallel or len(tier) <= 1:
                for name, extractor in tier:
                    results[name] = self._safe_extract(name, extractor, index, classification, context, registry)
                continue

            with ThreadPoolExecutor(max_workers=self._config.max_parallel_workers) as executor:
                futures = {
                    executor.submit(self._safe_extract, name, extractor, index, classification, context, registry): name
                    for name, extractor in tier
                }
                for future, name in futures.items():
                    results[name] = future.result()
        return results

    @staticmethod
    def _tiers(enabled: list[tuple[str, BaseExtractor]]) -> list[list[tuple[str, BaseExtractor]]]:
        """Groups `enabled` (already sorted descending by priority — see
        get_enabled()) into consecutive same-priority runs, preserving
        that descending order between groups."""
        tiers: list[list[tuple[str, BaseExtractor]]] = []
        for name, extractor in enabled:
            if tiers and tiers[-1][-1][1].priority() == extractor.priority():
                tiers[-1].append((name, extractor))
            else:
                tiers.append([(name, extractor)])
        return tiers

    @staticmethod
    def _safe_extract(
        name: str,
        extractor: BaseExtractor,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        try:
            return extractor.extract(index, classification, context, registry)
        except Exception as exc:  # noqa: BLE001 -- one extractor's crash must never take down the others
            error = ExtractionError(
                extractor=name,
                error_type=ErrorType.EXTRACTION_ERROR,
                message=str(exc),
                severity=ErrorSeverity.ERROR,
            )
            return ExtractionResult(errors=[error])
