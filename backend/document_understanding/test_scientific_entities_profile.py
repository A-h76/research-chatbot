"""Unit tests for scientific_entities_profile (Paper Analysis 2.6)."""

from backend.document_understanding.scientific_entities_profile import (
    extract_scientific_entities_profile,
)


def test_projects_methodology_and_stats_into_entities():
    du = {
        "methodology_profile": {
            "has_content": True,
            "study_design": {"text": "cohort", "label": "cohort", "confidence": 0.9},
            "dataset": {"text": "ImageNet benchmark corpus", "confidence": 0.8},
            "metrics": [{"text": "accuracy", "confidence": 0.8}],
            "variables": [{"text": "independent variable: dose", "confidence": 0.7}],
            "population": {"text": "adults with hypertension", "confidence": 0.75},
        },
        "statistics_profile": {
            "has_content": True,
            "tests": [{"text": "ANOVA", "label": "anova", "confidence": 0.88}],
            "effect_sizes": [{"text": "HR = 1.45", "confidence": 0.85}],
        },
    }
    out = extract_scientific_entities_profile(du)
    assert out["has_content"] is True
    types = {e["entity_type"] for e in out["entities"]}
    assert "method" in types
    assert "dataset" in types
    assert "metric" in types
    assert "statistic" in types
    assert out["relations"]
    assert any(r["predicate"] == "uses" for r in out["relations"])
    assert any(r["predicate"] == "measures" for r in out["relations"])


def test_invent_nothing_on_empty():
    out = extract_scientific_entities_profile({})
    assert out["has_content"] is False
    assert out["entities"] == []
    assert out["relations"] == []


def test_no_relation_without_both_ends():
    du = {
        "methodology_profile": {
            "study_design": {"text": "survey", "label": "survey", "confidence": 0.8},
        },
        "statistics_profile": {},
    }
    out = extract_scientific_entities_profile(du)
    assert out["entities"]
    assert out["relations"] == []


def test_medical_enrich_when_not_skipped():
    du = {
        "methodology_profile": {
            "study_design": {"text": "RCT", "label": "randomized_controlled_trial", "confidence": 0.9},
        }
    }
    medical = {
        "skipped": False,
        "pico_elements": {
            "intervention": {"label": "metformin"},
            "outcome": {"label": "HbA1c"},
        },
        "clinical_entities": [
            {"value": "type 2 diabetes", "entity_type": "condition", "confidence": 0.8},
        ],
    }
    out = extract_scientific_entities_profile(du, medical=medical)
    values = [e["value"].lower() for e in out["entities"]]
    assert any("metformin" in v for v in values)
    assert any("hba1c" in v for v in values)
    assert any("diabetes" in v for v in values)
    assert any(r["predicate"] == "targets" for r in out["relations"])


def test_skips_medical_when_skipped_flag():
    du = {"methodology_profile": {"dataset": {"text": "CIFAR-10", "confidence": 0.8}}}
    medical = {
        "skipped": True,
        "clinical_entities": [{"value": "should-not-appear", "entity_type": "condition"}],
    }
    out = extract_scientific_entities_profile(du, medical=medical)
    values = [e["value"].lower() for e in out["entities"]]
    assert "cifar-10" in values
    assert not any("should-not-appear" in v for v in values)


def test_attach_on_pipeline_phases():
    from backend.analysis_pipeline.service import (
        _attach_methodology_profile,
        _attach_scientific_entities_profile,
        _attach_statistics_profile,
    )

    phases = {
        "document_understanding": {
            "metadata": {"abstract": ""},
            "structure": {
                "normalized_headings": {
                    "methods": (
                        "We conducted a cohort study using the ImageNet dataset. "
                        "Primary metrics were accuracy and F1-score."
                    )
                },
                "raw_headings": {},
                "section_types": {},
            },
        }
    }
    _attach_methodology_profile(phases)
    _attach_statistics_profile(phases)
    _attach_scientific_entities_profile(phases)
    profile = phases["document_understanding"]["scientific_entities_profile"]
    assert profile["has_content"] is True
    assert profile["entities"]
