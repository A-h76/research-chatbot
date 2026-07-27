"""Performance benchmarking for DocumentClassificationPipeline — confirms
the <100ms-per-typical-paper target (see package docstring's Performance
Considerations) without a separate profiling dependency. Stdlib only.
"""

import time
from dataclasses import dataclass
from statistics import mean, median
from typing import Optional

from backend.document_understanding.models import ProcessedDocument

from .pipeline import DocumentClassificationPipeline


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
    pipeline: Optional[DocumentClassificationPipeline] = None,
    runs: int = 20,
    label: str = "document",
) -> BenchmarkResult:
    """Times `runs` calls to pipeline.process(document) — no warmup runs
    discarded, since this pipeline is pure in-memory computation (no I/O,
    no caching) with no cold-start effect worth excluding."""
    pipeline = pipeline or DocumentClassificationPipeline()
    durations_ms: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        pipeline.process(document)
        durations_ms.append((time.perf_counter() - start) * 1000)

    return BenchmarkResult(
        label=label,
        runs=runs,
        min_ms=min(durations_ms),
        max_ms=max(durations_ms),
        mean_ms=mean(durations_ms),
        median_ms=median(durations_ms),
    )


def benchmark_documents(
    documents: dict[str, ProcessedDocument],
    pipeline: Optional[DocumentClassificationPipeline] = None,
    runs: int = 20,
) -> list[BenchmarkResult]:
    """One BenchmarkResult per (label, document) pair in `documents` —
    convenience for benchmarking several sample papers in one call."""
    pipeline = pipeline or DocumentClassificationPipeline()
    return [benchmark_document(document, pipeline, runs, label) for label, document in documents.items()]
