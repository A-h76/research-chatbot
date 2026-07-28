"""Unit tests for Evidence Layer scoring, provenance, extract plan, explain assembly."""

from __future__ import annotations

from types import SimpleNamespace

from backend.evidence.extractor import build_candidate, run_extraction_plan
from backend.evidence.inspector import assemble_explain_response, compute_sufficiency
from backend.evidence.provenance import compute_content_hash
from backend.evidence.reviews import validate_review_payload
from backend.evidence.scoring import confidence_band_from_grades


def test_confidence_band_rct_high():
    assert (
        confidence_band_from_grades(study_type="RCT", study_quality="High", risk_of_bias="low")
        == "high"
    )


def test_confidence_band_contradiction_is_low():
    assert (
        confidence_band_from_grades(
            study_type="RCT", study_quality="High", has_contradiction=True
        )
        == "low"
    )


def test_confidence_band_missing_grades_not_high():
    assert confidence_band_from_grades() in {"low", "moderate"}
    assert confidence_band_from_grades() != "high"


def test_content_hash_stable():
    a = compute_content_hash(
        file_id=1, page=2, char_start=0, char_end=10, quote="Hello", claim="Claim"
    )
    b = compute_content_hash(
        file_id=1, page=2, char_start=0, char_end=10, quote=" hello ", claim="claim"
    )
    assert a == b


def test_build_candidate_requires_page_when_flagged():
    try:
        build_candidate(file_id=1, quote="q", claim="c", page=None, require_page=True)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_extraction_skips_when_not_research_ready():
    result = run_extraction_plan(
        is_research_ready=False,
        file_fingerprint="abc",
        build_candidates=lambda: [],
    )
    assert result["status"] == "skipped"


def test_extraction_idempotent_reuse():
    from backend.evidence.provenance import compute_input_content_hash

    h = compute_input_content_hash(file_fingerprint="abc", pipeline_version="2.2.0")
    result = run_extraction_plan(
        is_research_ready=True,
        file_fingerprint="abc",
        prior_run_succeeded=True,
        prior_input_hash=h,
        force=False,
        build_candidates=lambda: [_boom()],
    )
    assert result["reason"] == "idempotent_reuse"
    assert result["objects_created"] == 0


def _boom():
    raise AssertionError("should not build candidates on idempotent reuse")


def test_sufficiency_and_explain_order():
    rows = [
        SimpleNamespace(
            id=2,
            user_id=1,
            project_id=1,
            file_id=9,
            page=3,
            char_start=None,
            char_end=None,
            section="Results",
            quote="q2",
            claim="c2",
            study_type="RCT",
            study_quality="High",
            supports_json="[]",
            contradicts_json="[]",
            limitations_json="[]",
            confidence_band="high",
            status="candidate",
            pipeline_version="2.2.0",
            created_by="analysis-pipeline",
            content_hash="h2",
            supersedes_id=None,
            provenance_json='{"pipeline_version":"2.2.0"}',
            source_kg_node_id="",
        ),
        SimpleNamespace(
            id=1,
            user_id=1,
            project_id=1,
            file_id=9,
            page=1,
            char_start=None,
            char_end=None,
            section="Results",
            quote="q1",
            claim="c1",
            study_type="RCT",
            study_quality="High",
            supports_json="[]",
            contradicts_json="[]",
            limitations_json="[]",
            confidence_band="moderate",
            status="accepted",
            pipeline_version="2.2.0",
            created_by="analysis-pipeline",
            content_hash="h1",
            supersedes_id=None,
            provenance_json="{}",
            source_kg_node_id="",
        ),
    ]
    resp = assemble_explain_response(
        sentence={"block_id": "blk_1", "text": "hello"},
        bound_objects=rows,
        relations=["supports", "supports"],
        file_titles={9: "Paper"},
    )
    assert resp["sufficiency"] == "sufficient"
    assert resp["evidence"][0]["id"] == 1
    assert resp["evidence"][0]["status"] == "accepted"
    assert compute_sufficiency([]) == "insufficient"


def test_review_validation():
    assert validate_review_payload({"status": "accepted"})["status"] == "accepted"
    try:
        validate_review_payload({"status": "edited"})
        assert False
    except ValueError:
        pass
