from backend.medical_understanding.benchmark import benchmark_document
from backend.medical_understanding.conftest import process_pdf


def test_benchmark_document_returns_sane_timings(pdf_factory, classification_factory, context_factory):
    document = process_pdf(pdf_factory(["Abstract\nPatients with diabetes were treated with metformin.\n"]))
    result = benchmark_document(document, classification_factory(), context_factory(), runs=5, label="sample")

    assert result.label == "sample"
    assert result.runs == 5
    assert result.min_ms >= 0.0
    assert result.min_ms <= result.mean_ms <= result.max_ms
    assert result.median_ms >= 0.0
