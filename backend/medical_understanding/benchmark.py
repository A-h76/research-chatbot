"""Performance benchmarking for MedicalUnderstandingPipeline — confirms
the max_processing_time_ms target (config.py) without a separate
profiling dependency. Stdlib only.
"""

import time
from dataclasses import dataclass
from statistics import mean, median
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .pipeline import MedicalUnderstandingPipeline


@dataclass
class BenchmarkResult:
    """Wall-clock timing across `runs` calls to process() for one
    document."""

    label: str
    runs: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float


def benchmark_document(
    document: ProcessedDocument,
    classification: ClassificationResult,
    context: AnalysisContext,
    pipeline: Optional[MedicalUnderstandingPipeline] = None,
    runs: int = 20,
    label: str = "document",
) -> BenchmarkResult:
    """Times `runs` calls to pipeline.process(document, classification,
    context) — no warmup runs discarded, since this pipeline is pure
    in-memory computation (no I/O, no caching across calls) with no
    cold-start effect worth excluding."""
    pipeline = pipeline or MedicalUnderstandingPipeline()
    durations_ms: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        pipeline.process(document, classification, context)
        durations_ms.append((time.perf_counter() - start) * 1000)

    return BenchmarkResult(
        label=label,
        runs=runs,
        min_ms=min(durations_ms),
        max_ms=max(durations_ms),
        mean_ms=mean(durations_ms),
        median_ms=median(durations_ms),
    )
