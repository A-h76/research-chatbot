"""Unit tests for quality_assessment_profile (Paper Analysis 2.7)."""

from backend.document_understanding.quality_assessment_profile import (
    extract_quality_assessment_profile,
)


def test_builds_inspectable_checklist_without_numeric_score():
    du = {
        "methodology_profile": {
            "has_content": True,
            "study_design": {
                "text": "randomized controlled trial",
                "label": "randomized_controlled_trial",
                "confidence": 0.9,
            },
            "sample_size": {"text": "n = 240", "label": "240", "confidence": 0.85},
            "code_available": {
                "text": "Code is available at github.com/example",
                "label": "available",
            },
            "dataset_available": None,
            "metrics": [{"text": "accuracy"}],
        },
        "statistics_profile": {
            "has_content": True,
            "tests": [{"text": "ANOVA", "label": "anova"}],
            "p_values": [{"text": "p < 0.01"}],
            "confidence_intervals": [],
            "effect_sizes": [{"text": "HR = 1.45"}],
            "interpretations": [],
        },
        "limitations_novelty_profile": {
            "has_content": True,
            "limitations": [
                {
                    "text": "Single-center study with short follow-up.",
                    "author_stated": True,
                }
            ],
            "novelty": [],
            "future_work": [],
            "research_gaps": [],
        },
        "scientific_entities_profile": {"entities": [], "relations": []},
    }
    out = extract_quality_assessment_profile(du)
    assert out["has_content"] is True
    assert out["scoring"] == "inspectable_checklist"
    assert "overall_score" not in out
    assert "score" not in out

    by_id = {s["id"]: s for s in out["sections"]}
    assert by_id["methodology"]["band"] in {"strong", "partial", "weak", "unknown"}
    assert any(i["status"] == "pass" for i in by_id["methodology"]["items"])
    assert any("randomized" in i["text"].lower() for i in by_id["methodology"]["items"])

    assert any(i["status"] == "pass" for i in by_id["evidence"]["items"])
    assert any("Statistical analysis" in i["text"] for i in by_id["evidence"]["items"])
    assert any(i["status"] == "pass" and "Large sample" in i["text"] for i in by_id["evidence"]["items"])

    assert any("Single-center" in i["text"] for i in by_id["limitations"]["items"])
    assert any(i["status"] == "pass" and "Code" in i["text"] for i in by_id["availability"]["items"])
    assert any(
        i["status"] == "missing" and "Dataset" in i["text"] for i in by_id["availability"]["items"]
    )


def test_invent_nothing_empty_profiles():
    out = extract_quality_assessment_profile({})
    assert out["scoring"] == "inspectable_checklist"
    # Still returns sections with missing notes — inspectable empty, not inventing strength.
    by_id = {s["id"]: s for s in out["sections"]}
    assert by_id["methodology"]["band"] in {"unknown", "weak", "partial"}
    assert all("reason" in i for i in by_id["methodology"]["items"])


def test_every_item_has_reason():
    du = {
        "methodology_profile": {
            "study_design": {"text": "cohort", "label": "cohort"},
        },
        "statistics_profile": {"tests": [{"text": "t-test", "label": "t_test"}]},
        "limitations_novelty_profile": {"limitations": []},
    }
    out = extract_quality_assessment_profile(du)
    for section in out["sections"]:
        for item in section["items"]:
            assert item.get("reason")
            assert item.get("status") in {"pass", "note", "missing"}


def test_attach_on_pipeline_phases():
    from backend.analysis_pipeline.service import (
        _attach_methodology_profile,
        _attach_quality_assessment_profile,
        _attach_scientific_entities_profile,
        _attach_statistics_profile,
    )

    phases = {
        "document_understanding": {
            "metadata": {"abstract": ""},
            "structure": {
                "normalized_headings": {
                    "methods": (
                        "We conducted a randomized controlled trial with n = 120 patients. "
                        "Primary metrics were accuracy."
                    ),
                    "results": "Group differences used ANOVA (p < 0.05).",
                },
                "raw_headings": {},
                "section_types": {},
            },
        }
    }
    _attach_methodology_profile(phases)
    _attach_statistics_profile(phases)
    _attach_scientific_entities_profile(phases)
    _attach_quality_assessment_profile(phases)
    qa = phases["document_understanding"]["quality_assessment_profile"]
    assert qa["has_content"] is True
    assert qa["scoring"] == "inspectable_checklist"
    assert "overall_score" not in qa
