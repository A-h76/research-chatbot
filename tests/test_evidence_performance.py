"""Stage 4 performance smoke — measure Explain + extract (not estimates)."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import statistics
import time

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server
from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult
from backend.analysis_pipeline.persistence import load_analysis_result, save_analysis_result
from backend.evidence.services.extract_service import run_evidence_extraction


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _ms(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000


def _percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def _seed_explain_world(user_id: int, *, binding_count: int = 20):
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=user_id,
                email=f"perf{user_id}@example.com",
                name=f"Perf {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"PerfP{user_id}", emoji="P")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Perf",
            content="x" * 5000,
            status="active",
            current_version=1,
            last_saved_hash="p",
        )
        db.add(doc)
        uf = server.UserFile(
            user_id=user_id,
            project_id=project.id,
            name="perf.pdf",
            title="Perf Paper",
            path="/tmp/perf.pdf",
            size=1000,
            meta_status="done",
            kind="document",
        )
        db.add(uf)
        db.flush()
        for i in range(binding_count):
            ev = server.EvidenceObject(
                user_id=user_id,
                project_id=project.id,
                file_id=uf.id,
                page=i + 1,
                quote=f"quote {i} " + ("word " * 20),
                claim=f"claim {i}",
                confidence_band="moderate",
                status="accepted",
                pipeline_version="2.2.0",
                content_hash=f"perf-{user_id}-{i}",
                provenance_json='{"pipeline_version":"2.2.0"}',
            )
            db.add(ev)
            db.flush()
            db.add(
                server.WritingSentenceBinding(
                    user_id=user_id,
                    project_id=project.id,
                    document_id=doc.id,
                    evidence_object_id=ev.id,
                    block_id="blk_perf",
                    selected_text="shared selection",
                    relation="supports",
                )
            )
        db.commit()
        return {"project_id": project.id, "document_id": doc.id, "file_id": uf.id}
    finally:
        db.close()


def test_explain_p50_p95_budget():
    seeded = _seed_explain_world(6001, binding_count=20)
    client = _client()
    _login(client, 6001)
    body = {
        "document_id": seeded["document_id"],
        "project_id": seeded["project_id"],
        "block_id": "blk_perf",
        "selected_text": "shared selection",
    }
    # Warmup
    assert client.post("/api/evidence/explain", json=body).status_code == 200

    samples = []
    for _ in range(25):
        resp, elapsed = _ms(lambda: client.post("/api/evidence/explain", json=body))
        assert resp.status_code == 200
        assert resp.get_json()["sufficiency"] == "sufficient"
        samples.append(elapsed)

    samples.sort()
    p50 = _percentile(samples, 0.50)
    p95 = _percentile(samples, 0.95)
    # QA target: p95 < 300ms warm local (document measured values)
    assert p50 < 300, f"explain p50 too high: {p50:.1f}ms samples={samples[:5]}…"
    assert p95 < 500, f"explain p95 too high: {p95:.1f}ms (budget 500ms smoke)"
    # Attach for Stage 4 evidence note consumers
    print(f"EXPLAIN_PERF p50={p50:.2f}ms p95={p95:.2f}ms mean={statistics.mean(samples):.2f}ms n={len(samples)}")


def test_extraction_throughput_single_paper():
    uid = 6002
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=uid,
                email=f"perf{uid}@example.com",
                name="x",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=uid, name="ex", emoji="E")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=uid,
            project_id=project.id,
            name="big.pdf",
            title="Large",
            path="/tmp/big.pdf",
            size=5_000_000,
            meta_status="done",
            kind="document",
            content_hash="large-hash",
        )
        db.add(uf)
        db.flush()
        db.add(server.Chunk(file_id=uf.id, idx=0, content="chunk " * 500, page=1))
        # Many claim nodes to stress projector
        nodes = []
        edges = []
        for i in range(40):
            nid = f"c{i}"
            nodes.append(
                {
                    "node_id": nid,
                    "node_type": "evidence_claim",
                    "label": f"Claim {i}",
                    "evidence_references": [
                        {
                            "page": (i % 10) + 1,
                            "text_snippet": f"Finding number {i} with detail " * 5,
                            "character_range": [i * 10, i * 10 + 20],
                        }
                    ],
                }
            )
            edges.append(
                {
                    "edge_id": f"e{i}",
                    "source_node_id": nid,
                    "target_node_id": "o0",
                    "edge_type": "supports",
                }
            )
        nodes.append({"node_id": "o0", "node_type": "outcome", "label": "O", "evidence_references": []})
        save_analysis_result(
            db,
            server.AnalysisPipelineResult,
            AnalysisResult(
                file_id=uf.id,
                content_hash="large-hash",
                status=AnalysisJobStatus.DONE,
                phase_results={
                    "classification": {"study_design": {"label": "cohort"}},
                    "evidence_grading": {"study_quality": "moderate"},
                    "knowledge_graph": {"version": "1.0.0", "nodes": nodes, "edges": edges},
                },
                pipeline_version="2.0.0",
                total_processing_time_ms=1,
            ),
            user_id=uid,
        )
        db.commit()
        pid, fid = project.id, uf.id
    finally:
        db.close()

    db = server.SessionLocal()
    try:
        result, elapsed = _ms(
            lambda: run_evidence_extraction(
                db,
                user_id=uid,
                project_id=pid,
                file_id=fid,
                UserFile=server.UserFile,
                AnalysisPipelineResult=server.AnalysisPipelineResult,
                EvidenceObject=server.EvidenceObject,
                EvidenceExtractionRun=server.EvidenceExtractionRun,
                load_analysis_result=load_analysis_result,
            )
        )
        assert result["status"] == "succeeded"
        assert result["objects_created"] == 40
        # Single-paper extract smoke budget (local SQLite)
        assert elapsed < 5000, f"extract too slow: {elapsed:.1f}ms"
        print(f"EXTRACT_PERF objects={result['objects_created']} elapsed_ms={elapsed:.2f}")
    finally:
        db.close()
