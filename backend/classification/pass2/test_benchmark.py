from backend.classification.pass2.benchmark import benchmark_document, benchmark_documents


def test_benchmark_document_returns_sane_timings(document_factory):
    document = document_factory(full_text="We conducted a randomized controlled trial." * 20)
    result = benchmark_document(document, runs=5, label="sample")

    assert result.label == "sample"
    assert result.runs == 5
    assert result.min_ms >= 0.0
    assert result.min_ms <= result.mean_ms <= result.max_ms
    assert result.median_ms >= 0.0


def test_benchmark_documents_returns_one_result_per_document(document_factory):
    documents = {
        "a": document_factory(full_text="alpha"),
        "b": document_factory(full_text="beta"),
    }
    results = benchmark_documents(documents, runs=3)
    assert {r.label for r in results} == {"a", "b"}
    assert all(r.runs == 3 for r in results)
