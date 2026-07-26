"""Performance benchmarking for KnowledgeGraphPipeline."""

import time
from dataclasses import dataclass
from statistics import mean, median
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding
from backend.prompt_assembly.models import AssembledPrompt

from .pipeline import KnowledgeGraphPipeline


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
    prompt: AssembledPrompt,
    pipeline: Optional[KnowledgeGraphPipeline] = None,
    runs: int = 10,
    label: str = "document",
) -> BenchmarkResult:
    pipeline = pipeline or KnowledgeGraphPipeline()
    durations: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        pipeline.process(document, classification, context, medical, grades, prompt)
        durations.append((time.perf_counter() - start) * 1000)
    return BenchmarkResult(
        label=label,
        runs=runs,
        min_ms=min(durations),
        max_ms=max(durations),
        mean_ms=mean(durations),
        median_ms=median(durations),
    )
