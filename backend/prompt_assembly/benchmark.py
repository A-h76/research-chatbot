"""Performance benchmarking for PromptAssemblyPipeline."""

import time
from dataclasses import dataclass
from statistics import mean, median
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from .pipeline import PromptAssemblyPipeline


@dataclass
class BenchmarkResult:
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
    medical: MedicalUnderstanding,
    grades: EvidenceGrades,
    pipeline: Optional[PromptAssemblyPipeline] = None,
    runs: int = 20,
    label: str = "document",
) -> BenchmarkResult:
    pipeline = pipeline or PromptAssemblyPipeline()
    durations_ms: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        pipeline.process(document, classification, context, medical, grades)
        durations_ms.append((time.perf_counter() - start) * 1000)

    return BenchmarkResult(
        label=label,
        runs=runs,
        min_ms=min(durations_ms),
        max_ms=max(durations_ms),
        mean_ms=mean(durations_ms),
        median_ms=median(durations_ms),
    )
