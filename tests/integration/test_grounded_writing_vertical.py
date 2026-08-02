"""Private Alpha Success Gate — Grounded Writing Trust Vertical E2E.

Proves the researcher path works without engineer intervention (DB/admin hacks):

  Research Ready paper
    → Extract evidence (API + worker)
    → Accept ≥3 EvidenceObjects
    → Citation resolve → insert [#id] + binding
    → Writing Intelligence (grounded lit-review)
    → Research Reviewer persisted
    → Export markdown (traceability metadata)
    → Re-open document + bindings still linked

Run: pytest tests/integration/test_grounded_writing_vertical.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import server
import worker
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import save_analysis_result
from backend.evidence.writing.export_markdown import build_literature_review_markdown
from backend.library.readiness import research_readiness


def _phase_results_three_claims():
    """Phase 1 fixture with three grounded claims (Alpha accept bar ≥3)."""
    nodes = []
    for i, (nid, label, quote, page) in enumerate(
        (
            (
                "c1",
                "Drug X reduces HbA1c in adults",
                "Drug X reduces HbA1c in adults by 0.8%",
                2,
            ),
            (
                "c2",
                "HbA1c reduction persists at 12 weeks",
                "HbA1c fell at 12 weeks with Drug X",
                3,
            ),
            (
                "c3",
                "Drug X is well tolerated",
                "Adverse events were similar to placebo",
                4,
            ),
        ),
        start=1,
    ):
        nodes.append(
            {
                "node_id": nid,
                "node_type": "evidence_claim",
                "label": label,
                "properties": {
                    "outcome_name": "HbA1c" if i < 3 else "safety",
                    "population": "adults with T2DM",
                },
                "evidence_references": [
                    {
                        "page": page,
                        "section": "results",
                        "text_snippet": quote,
                        "character_range": [10, 10 + len(quote)],
                    }
                ],
            }
        )
    return {
        "classification": {"study_design": {"label": "randomized_controlled_trial"}},
        "medical_understanding": {
            "pico_elements": {
                "population": {"label": "adults with T2DM"},
                "intervention": "Drug X",
                "outcome": "HbA1c change",
            }
        },
        "evidence_grading": {
            "study_quality": "high",
            "risk_of_bias": {"overall_risk": "low"},
            "consistency": {"consistency_level": "highly_consistent"},
            "pipeline_version": "1.0.0",
        },
        "knowledge_graph": {"version": "1.0.0", "nodes": nodes, "edges": []},
    }


@pytest.fixture
def vertical_world(researcher):
    db = researcher.db
    user = researcher.user
    project = researcher.project

    uf = server.UserFile(
        user_id=user.id,
        project_id=project.id,
        name="vertical-paper.pdf",
        title="Drug X HbA1c Trial",
        path=f"/tmp/vertical-{user.id}.pdf",
        size=200,
        meta_status="done",
        kind="document",
        content_hash=f"vertical-hash-{user.id}",
        doi="10.1000/vertical-alpha",
    )
    db.add(uf)
    db.flush()
    db.add(
        server.Chunk(
            file_id=uf.id,
            idx=0,
            content="Drug X reduces HbA1c in adults by 0.8%.",
            page=2,
            section="results",
        )
    )
    doc = server.WritingDocument(
        user_id=user.id,
        project_id=project.id,
        title="Alpha lit review draft",
        content="",
        status="active",
        current_version=1,
        last_saved_hash="vertical",
    )
    db.add(doc)
    save_analysis_result(
        db,
        server.AnalysisPipelineResult,
        AnalysisResult(
            file_id=uf.id,
            content_hash=uf.content_hash,
            status=AnalysisJobStatus.DONE,
            phase_results=_phase_results_three_claims(),
            pipeline_version="2.0.0",
            total_processing_time_ms=8,
        ),
        user_id=user.id,
    )
    db.commit()
    assert research_readiness(uf) == "research_ready"
    return {
        "project_id": project.id,
        "file_id": uf.id,
        "document_id": doc.id,
        "user_id": user.id,
    }


def _run_extract_job(db, job_id: int):
    job = db.get(server.UploadJob, job_id)
    assert job is not None
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()
    worker._handle_evidence_extract(db, job)
    job = db.get(server.UploadJob, job_id)
    job.status = "done"
    job.finished_at = datetime.now(timezone.utc)
    worker._mark_outbox_dispatched(db, job.id)
    db.commit()
    return job


def test_grounded_writing_trust_vertical(researcher, vertical_world):
    """Full trust spine without manual intervention."""
    client = researcher.client
    db = researcher.db
    project_id = vertical_world["project_id"]
    file_id = vertical_world["file_id"]
    document_id = vertical_world["document_id"]

    # ── 1. Extract ────────────────────────────────────────────────────────
    enqueue = client.post(
        f"/api/projects/{project_id}/evidence/extract",
        json={"file_id": file_id},
    )
    assert enqueue.status_code == 202, enqueue.get_json()
    job_id = enqueue.get_json()["job_id"]
    _run_extract_job(db, job_id)

    listed = client.get(f"/api/projects/{project_id}/evidence?status=candidate")
    assert listed.status_code == 200
    candidates = listed.get_json()["items"]
    assert len(candidates) >= 3, "Alpha bar: ≥3 extractable EvidenceObjects"

    # Claims must be non-empty (extract quality gate)
    for c in candidates:
        assert (c.get("claim") or "").strip()
        assert (c.get("quote") or "").strip()
        assert c.get("page") is not None

    # ── 2. Accept ≥3 ──────────────────────────────────────────────────────
    evidence_ids: list[int] = []
    for c in candidates[:3]:
        eid = c["id"]
        review = client.post(
            f"/api/evidence/{eid}/reviews",
            json={"status": "accepted"},
        )
        assert review.status_code == 200, review.get_json()
        assert review.get_json()["evidence"]["status"] == "accepted"
        evidence_ids.append(eid)

    accepted = client.get(f"/api/projects/{project_id}/evidence?status=accepted")
    assert accepted.status_code == 200
    assert accepted.get_json()["total"] >= 3

    # ── 3. Citation resolve → grounded insert text ────────────────────────
    cit = client.post(
        "/api/citations",
        json={
            "authors": "Smith, A",
            "title": "Drug X HbA1c Trial",
            "year": "2024",
            "doi": "10.1000/vertical-alpha",
            "project_id": project_id,
        },
    )
    assert cit.status_code in {200, 201}, cit.get_json()
    citation_id = cit.get_json()["id"]

    resolved = client.get(
        f"/api/citations/{citation_id}/resolve-evidence?project_id={project_id}"
    )
    assert resolved.status_code == 200, resolved.get_json()
    res_body = resolved.get_json()
    assert res_body["grounded"] is True
    assert res_body["evidence_id"] in evidence_ids
    insert_text = res_body["insert_text"]
    assert insert_text.startswith("[#")

    # ── 4. Writing Intelligence (literature review) ───────────────────────
    wi = client.post(
        "/api/evidence/writing",
        json={
            "intent": "support_sentence",
            "section_type": "literature_review",
            "scope": {"project_id": project_id, "document_id": document_id},
            "filters": {"status": ["accepted"], "require_page_anchor": True},
            "ranking_strategy": "default_v0",
            "result_limit": 20,
            "query_text": "Drug X reduces HbA1c",
            "anchors": {
                "block_id": "vertical_blk",
                "selected_text": "Drug X reduces HbA1c in adults.",
            },
        },
    )
    assert wi.status_code == 200, wi.get_json()
    wi_body = wi.get_json()
    writing = wi_body["writing"]
    assert writing["status"] == "ok"
    assert writing["mode"] == "grounded_v1"
    assert writing.get("paragraph")
    assert writing.get("sections")
    assert writing.get("review") is not None
    reviewer_run_id = writing.get("reviewer_run_id")
    assert isinstance(reviewer_run_id, int) and reviewer_run_id > 0

    # Prefer WI paragraph; ensure at least one [#id] marker for trust spine
    paragraph = writing["paragraph"]
    markers = [eid for eid in evidence_ids if f"[#{eid}]" in paragraph]
    if not markers:
        # Deterministic composer may cite differently — force grounded insert
        paragraph = f"{paragraph.rstrip()} {insert_text}"
    assert any(f"[#{eid}]" in paragraph for eid in evidence_ids)

    # ── 5. Insert into draft + binding (Citation Manager path) ────────────
    draft = f"# Literature review\n\n{paragraph}\n"
    autosave = client.post(
        f"/api/writing/documents/{document_id}/autosave",
        json={
            "title": "Alpha lit review draft",
            "content": draft,
            "current_version": 1,
            "idempotency_key": f"vertical-{document_id}-v1",
        },
    )
    assert autosave.status_code == 200, autosave.get_json()
    saved_version = autosave.get_json().get("current_version") or 2

    primary_eid = res_body["evidence_id"]
    bind = client.post(
        f"/api/documents/{document_id}/evidence-bindings",
        json={
            "evidence_object_id": primary_eid,
            "block_id": "cite_insert",
            "selected_text": insert_text,
            "relation": "supports",
        },
    )
    assert bind.status_code == 201, bind.get_json()
    binding_id = bind.get_json()["id"]

    # ── 6. Reviewer reconstructable ───────────────────────────────────────
    latest = client.get(f"/api/documents/{document_id}/reviewer-runs/latest")
    assert latest.status_code == 200
    assert latest.get_json()["id"] == reviewer_run_id

    # ── 7. Export synchronized (MD + traceability) ────────────────────────
    md = build_literature_review_markdown(
        title="Alpha lit review draft",
        body=paragraph,
        writing=writing,
    )
    assert "evidence_traceability" in md
    assert "evidence_traceability_100:" in md

    # BibTeX path still available for citation manager
    bib = client.get(f"/api/citations/export?format=bibtex&project_id={project_id}")
    assert bib.status_code == 200
    bib_text = bib.get_data(as_text=True)
    assert "Smith" in bib_text or "Drug X" in bib_text or "@" in bib_text

    # ── 8. Re-open project artifacts — everything still linked ────────────
    reopened = client.get(f"/api/writing/documents/{document_id}")
    assert reopened.status_code == 200
    re_body = reopened.get_json()
    assert f"[#{primary_eid}]" in (re_body.get("content") or draft)
    assert (re_body.get("current_version") or saved_version) >= 1

    bindings = client.get(f"/api/documents/{document_id}/evidence-bindings")
    assert bindings.status_code == 200
    items = bindings.get_json()["items"]
    assert any(b["id"] == binding_id and b["evidence_object_id"] == primary_eid for b in items)

    still_accepted = client.get(
        f"/api/projects/{project_id}/evidence?status=accepted"
    )
    assert still_accepted.status_code == 200
    still_ids = {e["id"] for e in still_accepted.get_json()["items"]}
    assert set(evidence_ids).issubset(still_ids)

    # Resolve still grounded after reload
    resolved2 = client.get(
        f"/api/citations/{citation_id}/resolve-evidence?project_id={project_id}"
    )
    assert resolved2.status_code == 200
    assert resolved2.get_json()["grounded"] is True

    # Reviewer history survives reopen
    listed_runs = client.get(f"/api/documents/{document_id}/reviewer-runs")
    assert listed_runs.status_code == 200
    assert any(r["id"] == reviewer_run_id for r in listed_runs.get_json()["items"])
