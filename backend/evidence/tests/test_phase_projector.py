"""Project Phase 1 JSON → EvidenceObject candidates (quality regressions)."""

from backend.evidence.phase_projector import (
    candidates_from_phase_results,
    normalize_claim,
    normalize_study_type,
)


def test_projects_evidence_claim_nodes():
    phase = {
        "classification": {"study_design": {"label": "randomized_controlled_trial"}},
        "evidence_grading": {
            "study_quality": "high",
            "risk_of_bias": {"overall_risk": "low"},
            "consistency": {"consistency_level": "highly_consistent"},
            "pipeline_version": "1.0.0",
        },
        "knowledge_graph": {
            "version": "1.0.0",
            "nodes": [
                {
                    "node_id": "c1",
                    "node_type": "evidence_claim",
                    "label": "HbA1c decreased",
                    "properties": {"outcome_name": "HbA1c"},
                    "evidence_references": [
                        {
                            "page": 3,
                            "section": "results",
                            "text_snippet": "HbA1c decreased by 0.8%",
                            "character_range": [10, 40],
                        }
                    ],
                },
                {"node_id": "o1", "node_type": "outcome", "label": "HbA1c", "evidence_references": []},
            ],
            "edges": [
                {
                    "edge_id": "e1",
                    "source_node_id": "c1",
                    "target_node_id": "o1",
                    "edge_type": "supports",
                }
            ],
        },
    }
    cands = candidates_from_phase_results(file_id=9, phase_results=phase)
    assert len(cands) == 1
    assert cands[0].page == 3
    assert "HbA1c" in cands[0].quote
    assert cands[0].claim == "HbA1c decreased"
    assert cands[0].study_type == "randomized_controlled_trial"
    assert cands[0].confidence_band == "high"
    assert cands[0].supports == ["HbA1c"]
    assert cands[0].provenance.get("outcome") == "HbA1c"
    assert cands[0].provenance.get("method") == "randomized_controlled_trial"
    assert cands[0].provenance.get("extraction_prompt_version") == "phase_projector.v1.2"


def test_skips_ungrounded_claim():
    phase = {
        "knowledge_graph": {
            "nodes": [
                {
                    "node_id": "c1",
                    "node_type": "evidence_claim",
                    "label": "floating",
                    "evidence_references": [],
                }
            ],
            "edges": [],
        }
    }
    assert candidates_from_phase_results(file_id=1, phase_results=phase) == []


def test_normalize_claim_prefers_distinct_label():
    assert (
        normalize_claim(
            label="Drug X reduces HbA1c",
            outcome_name="HbA1c",
            quote="Drug X reduces HbA1c in adults with T2DM (p<0.01).",
        )
        == "Drug X reduces HbA1c"
    )


def test_normalize_claim_rejects_trivial():
    assert normalize_claim(label="  ", outcome_name="", quote="") is None
    assert normalize_claim(label="...", outcome_name="", quote="") is None


def test_normalize_study_type_aliases():
    assert normalize_study_type("Randomized Controlled Trial") == "randomized_controlled_trial"
    assert normalize_study_type("RCT") == "randomized_controlled_trial"
    assert normalize_study_type("meta-analysis") == "meta_analysis"
    assert normalize_study_type("prospective cohort") == "cohort"


def test_claim_equals_quote_flagged_in_provenance():
    phase = {
        "classification": {"study_design": "cohort study"},
        "knowledge_graph": {
            "nodes": [
                {
                    "node_id": "c1",
                    "node_type": "evidence_claim",
                    "label": "same text as quote",
                    "properties": {},
                    "evidence_references": [
                        {"page": 1, "text_snippet": "same text as quote"},
                    ],
                }
            ],
            "edges": [],
        },
    }
    cands = candidates_from_phase_results(file_id=2, phase_results=phase)
    assert len(cands) == 1
    assert cands[0].claim == cands[0].quote
    assert cands[0].provenance.get("claim_equals_quote") is True
    assert cands[0].study_type == "cohort"


def test_facets_from_pico_and_props():
    phase = {
        "classification": {"study_design": {"label": "RCT"}},
        "medical_understanding": {
            "pico_elements": {
                "population": {"label": "adults with T2DM"},
                "intervention": "metformin 1000mg",
                "outcome": "HbA1c change",
            }
        },
        "knowledge_graph": {
            "nodes": [
                {
                    "node_id": "c1",
                    "node_type": "evidence_claim",
                    "label": "Metformin lowered HbA1c",
                    "properties": {"follow_up": "12 weeks"},
                    "evidence_references": [
                        {"page": 4, "text_snippet": "Mean HbA1c fell 0.9% at 12 weeks."},
                    ],
                }
            ],
            "edges": [],
        },
    }
    cands = candidates_from_phase_results(file_id=3, phase_results=phase)
    assert len(cands) == 1
    prov = cands[0].provenance
    assert prov.get("population") == "adults with T2DM"
    assert "metformin" in (prov.get("dosage") or "").lower()
    assert prov.get("outcome") == "HbA1c change"
    assert prov.get("timeframe") == "12 weeks"
    assert cands[0].study_type == "randomized_controlled_trial"


def test_eg_fallback_uses_summary_when_no_claim_nodes():
    phase = {
        "classification": {"study_design": "systematic review"},
        "evidence_grading": {
            "study_quality": "moderate",
            "overall_grade": {
                "summary": "Intervention improves outcome",
                "evidence": [
                    {"page": 2, "text_snippet": "Pooled RR 0.72 (95% CI 0.60–0.86)."},
                ],
            },
        },
        "knowledge_graph": {"nodes": [], "edges": []},
    }
    cands = candidates_from_phase_results(file_id=4, phase_results=phase)
    assert len(cands) == 1
    assert cands[0].claim == "Intervention improves outcome"
    assert cands[0].study_type == "systematic_review"
    assert cands[0].source_kg_node_id == "eg_ref:0"
    assert cands[0].provenance.get("confidence")
    assert cands[0].provenance.get("quote")


def test_methodology_and_stats_enrich_facets():
    phase = {
        "classification": {},
        "document_understanding": {
            "methodology_profile": {
                "has_content": True,
                "study_design": {
                    "text": "cohort",
                    "label": "cohort",
                    "kind": "study_design",
                },
                "population": {"text": "adults with hypertension"},
                "sample_size": {"text": "n = 500", "label": "500"},
            },
            "statistics_profile": {
                "has_content": True,
                "p_values": [{"text": "p < 0.01"}],
                "tests": [{"text": "ANOVA", "label": "anova"}],
                "effect_sizes": [],
            },
        },
        "knowledge_graph": {
            "nodes": [
                {
                    "node_id": "c1",
                    "node_type": "evidence_claim",
                    "label": "BP reduced",
                    "properties": {
                        "limitations": ["Single-center enrollment only"],
                    },
                    "evidence_references": [
                        {"page": 5, "text_snippet": "Systolic BP fell by 8 mmHg."},
                    ],
                }
            ],
            "edges": [],
        },
    }
    cands = candidates_from_phase_results(file_id=5, phase_results=phase)
    assert len(cands) == 1
    prov = cands[0].provenance
    assert cands[0].study_type == "cohort"
    assert "cohort" in (prov.get("method") or "").lower()
    assert "hypertension" in (prov.get("population") or "").lower()
    assert prov.get("sample_size")
    assert prov.get("statistical_signals")
    assert cands[0].limitations
    assert "Single-center" in cands[0].limitations[0]


def test_candidate_cap_limits_noise():
    nodes = []
    for i in range(40):
        nodes.append(
            {
                "node_id": f"c{i}",
                "node_type": "evidence_claim",
                "label": f"Claim number {i} about outcome",
                "properties": {},
                "evidence_references": [
                    {"page": (i % 5) + 1, "text_snippet": f"Quote text for claim {i} with enough chars."},
                ],
            }
        )
    phase = {
        "classification": {"study_design": "rct"},
        "evidence_grading": {"study_quality": "high"},
        "knowledge_graph": {"nodes": nodes, "edges": []},
    }
    cands = candidates_from_phase_results(file_id=6, phase_results=phase, max_candidates=10)
    assert len(cands) == 10
