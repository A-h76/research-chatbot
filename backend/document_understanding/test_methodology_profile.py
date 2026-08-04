"""Unit tests for methodology_profile (Paper Analysis 2.2)."""

from backend.document_understanding.methodology_profile import extract_methodology_profile


def _du_payload(methods: str, abstract: str = "") -> dict:
    return {
        "metadata": {"abstract": abstract, "title": "Study"},
        "structure": {
            "heading_order": ["Methods"],
            "raw_headings": {"Methods": methods},
            "section_types": {"Methods": "methods"},
            "normalized_headings": {"methods": methods},
        },
    }


def test_extracts_rct_sample_size_and_control():
    methods = (
        "We conducted a randomized controlled trial. "
        "A total of 240 participants with type 2 diabetes were enrolled. "
        "The intervention was metformin plus counseling; the control group received usual care. "
        "Primary metrics were HbA1c and accuracy of adherence self-report."
    )
    out = extract_methodology_profile(_du_payload(methods))
    assert out["has_content"] is True
    assert out["study_design"]["label"] == "randomized_controlled_trial"
    assert out["sample_size"]["label"] == "240"
    assert out["controls"] is not None
    assert "control" in out["controls"]["text"].lower()
    assert out["metrics"]
    assert any("accuracy" in (m.get("text") or "").lower() for m in out["metrics"])


def test_classification_study_design_preferred():
    out = extract_methodology_profile(
        _du_payload("We analyzed survey responses from students."),
        classification={"study_design": {"label": "cohort", "confidence": 0.91}},
    )
    assert out["study_design"]["source"] == "classification"
    assert out["study_design"]["label"] == "cohort"


def test_code_and_dataset_availability_author_stated():
    methods = (
        "Experimental setup used PyTorch. "
        "Code is available at https://github.com/example/repo. "
        "The dataset is publicly available on Zenodo."
    )
    out = extract_methodology_profile(_du_payload(methods))
    assert out["code_available"]["label"] == "available"
    assert out["dataset_available"]["label"] == "available"


def test_invent_nothing_on_empty():
    out = extract_methodology_profile({"metadata": {}, "structure": {}})
    assert out["has_content"] is False
    assert out["study_design"] is None
    assert out["sample_size"] is None
    assert out["variables"] == []
    assert out["metrics"] == []


def test_attach_on_pipeline_phases():
    from backend.analysis_pipeline.service import _attach_methodology_profile

    phases = {
        "document_understanding": _du_payload(
            "A cohort study enrolled n = 50 patients. Control group received placebo."
        ),
        "classification": {"study_design": {"label": "cohort_study", "confidence": 0.8}},
    }
    _attach_methodology_profile(phases)
    profile = phases["document_understanding"]["methodology_profile"]
    assert profile["has_content"] is True
    assert profile["study_design"]["source"] == "classification"
    assert profile["sample_size"] is not None
