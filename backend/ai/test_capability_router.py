"""AI Capability Router v1.0 + AI Ledger tests."""

from __future__ import annotations

from backend.ai.ai_ledger import (
    AILedgerEntry,
    clear_ledger_for_tests,
    hash_output,
    recent_executions,
    record_execution,
)
from backend.ai.capability_router import (
    ACR_STATUS,
    ACR_VERSION,
    Capability,
    ExecutionPolicy,
    ExecutionProfile,
    Provider,
    ReasoningDepth,
    ResearchJob,
    resolve_execution,
)
from backend.ai.capability_router.resolve import (
    execution_policy_from_mode,
    legacy_gateway_task,
    legacy_quality_mode,
)


def test_acr_v1_frozen():
    assert ACR_VERSION == "1.0"
    assert ACR_STATUS == "frozen_v1"


def test_compare_methodologies_resolves_reasoning():
    plan = resolve_execution("compare_papers", execution_policy="highest_quality")
    assert plan.research_job == ResearchJob.COMPARE_PAPERS
    assert plan.capability == Capability.SCIENTIFIC_REASONING
    assert plan.execution_policy == ExecutionPolicy.HIGHEST_QUALITY
    assert plan.execution_profile.reasoning == ReasoningDepth.DEEP
    assert plan.provider == Provider.OPENAI
    assert plan.prompt_name


def test_literature_review_quality_first():
    plan = resolve_execution(ResearchJob.LITERATURE_REVIEW, execution_policy="highest_quality")
    assert plan.capability == Capability.DEEP_SYNTHESIS
    assert plan.provider in (Provider.ANTHROPIC, Provider.OPENAI)
    assert plan.execution_profile.context.value == "large"


def test_bulk_extract_economy():
    plan = resolve_execution("bulk_processing")
    assert plan.capability == Capability.BULK_PROCESSING
    assert plan.execution_policy == ExecutionPolicy.LOWEST_COST
    assert "pro" not in plan.model.lower() or plan.provider == Provider.GOOGLE


def test_writing_prefers_academic_writing_capability():
    plan = resolve_execution("writing", execution_policy="balanced")
    assert plan.capability == Capability.ACADEMIC_WRITING


def test_profile_override():
    custom = ExecutionProfile(reasoning=ReasoningDepth.LIGHT, vision=True)
    plan = resolve_execution("ocr", execution_profile=custom)
    assert plan.execution_profile.vision is True
    assert plan.execution_profile.reasoning == ReasoningDepth.LIGHT


def test_provenance_includes_profile():
    plan = resolve_execution("reviewer")
    prov = plan.to_provenance(tokens=100, cost_usd=0.01, duration_ms=500)
    d = prov.to_dict()["ai_execution"]
    assert d["execution_profile"]["reasoning"]
    assert d["router_version"] == "1.0"


def test_profiles_are_not_model_brands():
    forbidden = {"sol", "fable", "gemini", "deepseek", "claude", "gpt", "kimi", "grok"}
    for cap in Capability:
        assert cap.value.lower() not in forbidden
        for token in forbidden:
            assert not cap.value.lower().startswith(token)


def test_legacy_bridge():
    assert legacy_gateway_task("literature_review") == "literature_review"
    assert legacy_quality_mode("highest_quality") == "publication"
    assert legacy_quality_mode("lowest_cost") == "fast"
    assert execution_policy_from_mode("publication") == ExecutionPolicy.HIGHEST_QUALITY
    assert execution_policy_from_mode("fast") == ExecutionPolicy.FASTEST
    assert execution_policy_from_mode("balanced") == ExecutionPolicy.BALANCED


def test_ai_ledger_records_execution():
    clear_ledger_for_tests()
    plan = resolve_execution("literature_review")
    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version="literature_review@v1",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.02,
        latency_ms=100,
        output_hash=hash_output("hello"),
    )
    recorded = record_execution(entry)
    assert recorded["execution_id"]
    assert recorded["research_job"] == "literature_review"
    assert recorded["execution_profile"]["reasoning"] == "deep"
    assert recent_executions(limit=1)[0]["prompt_version"] == "literature_review@v1"
