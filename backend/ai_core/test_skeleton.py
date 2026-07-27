"""Sprint 1 smoke — package imports and schema construction; no route wiring."""

from __future__ import annotations

from pathlib import Path

from backend.ai_core import (
    AIResponse,
    ResearchContext,
    WorkspaceReference,
    load_identity_pack,
)
from backend.ai_core.context import ResearchContextBuilder
from backend.ai_core.identity import identity_paths
from backend.ai_core.orchestration import IntentClassifier, PromptRouter, ResponseValidator
from backend.ai_core.schemas.ai_response import EvidenceReference
from backend.ai_core.schemas.research_context import ResearchIntent


def test_identity_files_exist():
    paths = identity_paths()
    assert len(paths) == 7
    for p in paths:
        assert p.is_file(), f"missing identity file: {p}"
        assert p.stat().st_size > 0


def test_research_context_constructs():
    ctx = ResearchContext(
        intent=ResearchIntent.WRITING,
        question="Draft a limitations paragraph",
        file_id=1,
    )
    assert ctx.intent is ResearchIntent.WRITING
    assert ctx.entities == []


def test_ai_response_and_workspace_ref_construct():
    ref = WorkspaceReference(
        id="wr-1",
        kind="evidence.outcome",
        ref_id="outcome-1",
        tab="evidence",
        label="Primary outcome",
    )
    resp = AIResponse(
        answer="Grounded draft.",
        confidence="Medium",
        evidence=[EvidenceReference(id="e1", label="Outcome row")],
        limitations=["Single paper context"],
        workspace_refs=[ref],
    )
    assert resp.confidence in ("High", "Medium", "Low")
    assert resp.workspace_refs[0].kind == "evidence.outcome"


def test_context_builder_runs_without_routes():
    ctx = ResearchContextBuilder().build(intent=ResearchIntent.EXPLAIN, file_id=7)
    assert ctx.file_id == 7
    pack = load_identity_pack()
    assert pack.identity and pack.principles and pack.policies


def test_orchestration_chain_constructs():
    assert IntentClassifier().classify("draft a paragraph") is ResearchIntent.WRITING
    ctx = ResearchContextBuilder().build(intent="reading", file_id=1)
    plan = PromptRouter().route(ctx.intent, ctx, question="Summarise")
    assert plan.template_key == "reading"
    result = ResponseValidator().validate(
        AIResponse(answer="ok", confidence="Low", limitations=["thin context"])
    )
    assert result.ok


def test_package_root_is_backend_ai_core():
    root = Path(__file__).resolve().parent
    assert root.name == "ai_core"
    assert (root / "identity" / "identity.md").is_file()
    assert (root / "context" / "compression.py").is_file()
