"""Tests for Research Memory promotion (Sprint C)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

import server
from backend.projects.memory import (
    claim_hash_for,
    create_memory_promotion_service,
)
from backend.ai.memory_engine import MemoryEngine
from backend.ai.prompt_builder import PromptBuilder


@pytest.fixture
def promo():
    return create_memory_promotion_service(
        SessionLocal=server.SessionLocal,
        select=select,
        Project=server.Project,
        UserFile=server.UserFile,
        Memory=server.Memory,
        DerivedAnalysis=server.DerivedAnalysis,
    )


@pytest.fixture
def researcher():
    db = server.SessionLocal()
    try:
        user = server.User(
            name="Mem Researcher",
            email=f"mem-{server.uuid.uuid4().hex[:8]}@test.local",
            picture="",
            auth_provider="dev",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        project = server.Project(
            user_id=user.id,
            name="Thesis",
            emoji="🔬",
            description="",
            instructions="",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        uid, pid = user.id, project.id
        paper_ids = []
        for i in range(2):
            f = server.UserFile(
                user_id=uid,
                project_id=pid,
                name=f"p{i}.pdf",
                kind="document",
                title=f"Paper {i}",
                meta_status="done",
                path=f"/tmp/p{i}.pdf",
                size=10,
            )
            db.add(f)
            db.commit()
            db.refresh(f)
            paper_ids.append(f.id)
    finally:
        db.close()

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = uid
    return {"user_id": uid, "project_id": pid, "client": client, "paper_ids": paper_ids}


def _seed_derived(uid, pid, paper_ids):
    db = server.SessionLocal()
    try:
        da = server.DerivedAnalysis(
            user_id=uid,
            project_id=pid,
            kind="research",
            selection_hash="abc",
            file_ids=json.dumps(paper_ids),
            data="{}",
            model="test",
        )
        db.add(da)
        db.commit()
        db.refresh(da)
        return da.id
    finally:
        db.close()


def test_promote_creates_finding_and_claims(promo, researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    papers = researcher["paper_ids"]
    da_id = _seed_derived(uid, pid, papers)

    result = {
        "summary": "Evidence is mixed across trials.",
        "answer": "Longer answer",
        "preset": "evidence",
        "supporting_file_ids": papers,
        "claims": [
            {
                    "claim": "Primary endpoint improved under the intervention arm.",
                "support": [
                    {
                        "paper_id": papers[0],
                        "title": "Paper 0",
                        "section": "results",
                        "snippet": "d=0.4",
                        "citation": "A 2020",
                    }
                ],
            }
        ],
    }
    out = promo.promote_research_result(
        user_id=uid, project_id=pid, derived_id=da_id, result=result
    )
    assert "error" not in out or out.get("error") is None
    assert out["total"] >= 2

    listed = promo.list_memories(pid, uid)
    assert listed is not None
    kinds = {m["kind"] for m in listed["items"]}
    assert "finding" in kinds
    assert "claim" in kinds
    for m in listed["items"]:
        assert m["source"] == "research"
        for paper_id in m["payload"].get("paper_ids") or []:
            assert paper_id in papers


def test_promote_disagree_is_contradiction(promo, researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    papers = researcher["paper_ids"]
    da_id = _seed_derived(uid, pid, papers)
    promo.promote_research_result(
        user_id=uid,
        project_id=pid,
        derived_id=da_id,
        result={
            "summary": "Disagreement summary",
            "preset": "disagree",
            "supporting_file_ids": papers,
            "claims": [
                {
                    "claim": "Authors report opposite directions of effect.",
                    "support": [{"paper_id": papers[0], "title": "P", "section": "", "snippet": "", "citation": ""}],
                }
            ],
        },
    )
    listed = promo.list_memories(pid, uid)
    claim_kinds = [m["kind"] for m in listed["items"] if m["kind"] != "finding"]
    assert "contradiction" in claim_kinds


def test_promote_idempotent_upsert(promo, researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    papers = researcher["paper_ids"]
    da_id = _seed_derived(uid, pid, papers)
    payload = {
        "summary": "Same summary every time.",
        "preset": "evidence",
        "supporting_file_ids": papers,
        "claims": [],
    }
    promo.promote_research_result(user_id=uid, project_id=pid, derived_id=da_id, result=payload)
    promo.promote_research_result(user_id=uid, project_id=pid, derived_id=da_id, result=payload)
    listed = promo.list_memories(pid, uid)
    findings = [m for m in listed["items"] if m["kind"] == "finding"]
    assert len(findings) == 1
    assert findings[0]["claim_hash"] == claim_hash_for("Same summary every time.")


def test_chat_memory_excluded_from_research_context(researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    db = server.SessionLocal()
    try:
        db.add(
            server.Memory(
                user_id=uid,
                project_id=pid,
                fact="I like APA citations",
                kind="fact",
                source="chat",
                status="active",
                claim_hash=claim_hash_for("I like APA citations"),
            )
        )
        db.add(
            server.Memory(
                user_id=uid,
                project_id=pid,
                fact="Metformin reduces HbA1c in adults.",
                kind="finding",
                source="research",
                status="active",
                pinned=1,
                claim_hash=claim_hash_for("Metformin reduces HbA1c in adults."),
                payload=json.dumps({"paper_ids": researcher["paper_ids"]}),
            )
        )
        db.commit()
        engine = MemoryEngine(db, server.Memory)
        ctx = engine.get_project_memory_context(uid, pid)
        facts = [m.fact for m in ctx]
        assert "Metformin reduces HbA1c in adults." in facts
        assert "I like APA citations" not in facts
    finally:
        db.close()


def test_prompt_builder_injects_research_memory(researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    db = server.SessionLocal()
    try:
        db.add(
            server.Memory(
                user_id=uid,
                project_id=pid,
                fact="Prior finding: dosing varies widely.",
                kind="finding",
                source="research",
                status="active",
                claim_hash=claim_hash_for("Prior finding: dosing varies widely."),
            )
        )
        db.commit()
        builder = server.get_prompt_builder(db)
        assembled = builder.build_chat_instructions(
            user_id=uid,
            user_name="R",
            project_id=pid,
            memory_enabled=True,
        )
        assert "Project Research Memory" in assembled.final
        assert "Prior finding: dosing varies widely." in assembled.final
        assert "developer context" in assembled.final.lower()
    finally:
        db.close()


def test_memory_http_pin_archive(promo, researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    papers = researcher["paper_ids"]
    da_id = _seed_derived(uid, pid, papers)
    promo.promote_research_result(
        user_id=uid,
        project_id=pid,
        derived_id=da_id,
        result={
            "summary": "HTTP memory summary",
            "preset": "evidence",
            "supporting_file_ids": papers,
            "claims": [],
        },
    )
    client = researcher["client"]
    listed = client.get(f"/api/projects/{pid}/memory")
    assert listed.status_code == 200
    items = listed.get_json()["items"]
    assert len(items) >= 1
    mid = items[0]["id"]

    pinned = client.patch(
        f"/api/projects/{pid}/memory/{mid}", json={"action": "pin"}
    )
    assert pinned.status_code == 200
    assert pinned.get_json()["pinned"] is True

    archived = client.patch(
        f"/api/projects/{pid}/memory/{mid}", json={"action": "archive"}
    )
    assert archived.status_code == 200
    assert archived.get_json()["status"] == "archived"

    # Soft delete
    deleted = client.delete(f"/api/projects/{pid}/memory/{mid}")
    assert deleted.status_code == 200
    again = client.get(f"/api/projects/{pid}/memory").get_json()["items"]
    assert all(m["id"] != mid for m in again)


def test_paper_ids_outside_project_stripped(promo, researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    papers = researcher["paper_ids"]
    da_id = _seed_derived(uid, pid, papers)
    promo.promote_research_result(
        user_id=uid,
        project_id=pid,
        derived_id=da_id,
        result={
            "summary": "Leakage check",
            "preset": "evidence",
            "supporting_file_ids": papers + [999999],
            "claims": [
                {
                    "claim": "Claim with bad paper",
                    "support": [
                        {"paper_id": 999999, "title": "X", "section": "", "snippet": "", "citation": ""},
                        {"paper_id": papers[0], "title": "Ok", "section": "", "snippet": "", "citation": ""},
                    ],
                }
            ],
        },
    )
    listed = promo.list_memories(pid, uid)
    for m in listed["items"]:
        for paper_id in m["payload"].get("paper_ids") or []:
            assert paper_id in papers
