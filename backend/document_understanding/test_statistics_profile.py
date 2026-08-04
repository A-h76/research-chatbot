"""Unit tests for statistics_profile (Paper Analysis 2.3)."""

from backend.document_understanding.statistics_profile import extract_statistics_profile


def _du_payload(*, results: str = "", abstract: str = "", methods: str = "") -> dict:
    headings: dict[str, str] = {}
    types: dict[str, str] = {}
    order: list[str] = []
    normalized: dict[str, str] = {}
    if results:
        order.append("Results")
        headings["Results"] = results
        types["Results"] = "results"
        normalized["results"] = results
    if methods:
        order.append("Methods")
        headings["Methods"] = methods
        types["Methods"] = "methods"
        normalized["methods"] = methods
    return {
        "metadata": {"abstract": abstract, "title": "Study"},
        "structure": {
            "heading_order": order,
            "raw_headings": headings,
            "section_types": types,
            "normalized_headings": normalized,
        },
    }


def test_extracts_p_ci_effect_and_test():
    results = (
        "Group differences were assessed with a two-way ANOVA. "
        "The primary outcome improved (p < 0.01; 95% CI 1.2-3.4; HR = 1.45). "
        "Cohen's d = 0.62."
    )
    out = extract_statistics_profile(_du_payload(results=results))
    assert out["has_content"] is True
    assert any(t.get("label") == "anova" for t in out["tests"])
    assert out["p_values"]
    assert any("p" in (p.get("text") or "").lower() for p in out["p_values"])
    assert out["confidence_intervals"]
    assert out["effect_sizes"]
    # No invented interpretation when author did not state significance wording.
    assert out["interpretations"] == []


def test_author_stated_interpretation_only():
    results = (
        "The treatment effect was statistically significant (p = 0.03). "
        "Secondary endpoints were not statistically significant."
    )
    out = extract_statistics_profile(_du_payload(results=results))
    assert out["p_values"]
    assert out["interpretations"]
    assert all(i.get("author_stated") is True for i in out["interpretations"])
    assert any("statistically significant" in (i.get("text") or "").lower() for i in out["interpretations"])


def test_does_not_invent_significance_from_p_alone():
    out = extract_statistics_profile(
        _du_payload(results="The mean change was 2.1 units (p = 0.04).")
    )
    assert out["p_values"]
    assert out["interpretations"] == []


def test_medical_measures_enrich():
    base = _du_payload(abstract="We observed improved outcomes.")
    medical = {
        "statistical_measures": [
            {"measure_type": "p_value", "value": "p<0.05", "confidence": 0.8},
            {"measure_type": "odds_ratio", "value": "OR=1.9", "confidence": 0.75},
        ]
    }
    out = extract_statistics_profile(base, medical=medical)
    assert out["has_content"] is True
    assert any(p.get("source") == "medical_understanding" for p in out["p_values"])
    assert any(e.get("source") == "medical_understanding" for e in out["effect_sizes"])


def test_invent_nothing_on_empty():
    out = extract_statistics_profile({"metadata": {}, "structure": {}})
    assert out["has_content"] is False
    assert out["tests"] == []
    assert out["p_values"] == []
    assert out["confidence_intervals"] == []
    assert out["effect_sizes"] == []
    assert out["interpretations"] == []


def test_attach_on_pipeline_phases():
    from backend.analysis_pipeline.service import _attach_statistics_profile

    phases = {
        "document_understanding": _du_payload(
            results="Chi-square tests showed association (p < 0.001; 95% CI 0.5-0.9)."
        ),
    }
    _attach_statistics_profile(phases)
    profile = phases["document_understanding"]["statistics_profile"]
    assert profile["has_content"] is True
    assert any(t.get("label") == "chi_square" for t in profile["tests"])
    assert profile["p_values"]
