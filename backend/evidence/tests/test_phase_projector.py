"""Project Phase 1 JSON → EvidenceObject candidates."""

from backend.evidence.phase_projector import candidates_from_phase_results


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
    assert cands[0].confidence_band == "high"
    assert cands[0].supports == ["HbA1c"]


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
