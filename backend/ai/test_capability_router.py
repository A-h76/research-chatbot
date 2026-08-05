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


def test_resolve_chat_execution_router_default():
    from backend.ai.capability_router.chat_resolve import (
        PROMPT_VERSION_CHAT,
        resolve_chat_execution,
    )

    plan = resolve_chat_execution(allowlisted_models=["gpt-5-mini", "gpt-5.5"])
    assert plan.research_job == ResearchJob.CHAT
    assert plan.capability == Capability.SCIENTIFIC_REASONING
    assert plan.model  # router-owned default
    assert PROMPT_VERSION_CHAT.startswith("chat@")


def test_resolve_chat_execution_allowlisted_override():
    from backend.ai.capability_router.chat_resolve import resolve_chat_execution

    plan = resolve_chat_execution(
        requested_model="gpt-5-mini",
        conversation_model="ignored-when-request-present",
        allowlisted_models=["gpt-5-mini", "gpt-4o"],
        execution_policy="balanced",
    )
    assert plan.model == "gpt-5-mini"
    assert plan.notes == "model_override"


def test_resolve_chat_execution_conversation_continuity():
    from backend.ai.capability_router.chat_resolve import resolve_chat_execution

    plan = resolve_chat_execution(
        requested_model=None,
        conversation_model="gpt-4o",
        allowlisted_models=["gpt-4o", "gpt-5-mini"],
    )
    assert plan.model == "gpt-4o"
    assert "override" in plan.notes


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


def test_ai_ledger_trace_and_status_fields():
    clear_ledger_for_tests()
    plan = resolve_execution("literature_review")
    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version="literature_review@v1",
        trace_id="trace-chat-1",
        parent_execution_id="parent-9",
        status="completed",
        latency_ms=42,
    )
    recorded = record_execution(entry)
    assert recorded["trace_id"] == "trace-chat-1"
    assert recorded["parent_execution_id"] == "parent-9"
    assert recorded["status"] == "completed"
    assert recorded["latency_ms"] == 42


def test_resolve_writing_assistant_grammar_uses_fastest():
    from backend.ai.capability_router.writing_resolve import resolve_writing_assistant_execution

    plan = resolve_writing_assistant_execution(action="improve_grammar")
    assert plan.research_job.value == "writing"
    assert plan.execution_policy.value == "fastest"


def test_resolve_writing_assistant_abstract_uses_highest_quality():
    from backend.ai.capability_router.writing_resolve import resolve_writing_assistant_execution

    plan = resolve_writing_assistant_execution(action="generate_abstract")
    assert plan.execution_policy.value == "highest_quality"


def test_resolve_writing_assistant_respects_quality_mode():
    from backend.ai.capability_router.writing_resolve import resolve_writing_assistant_execution

    plan = resolve_writing_assistant_execution(action="shorten", quality_mode="publication")
    assert plan.execution_policy.value == "highest_quality"


def test_resolve_reviewer_execution_default():
    from backend.ai.capability_router.reviewer_resolve import resolve_reviewer_execution

    plan = resolve_reviewer_execution()
    assert plan.research_job.value == "reviewer"
    assert plan.capability.value == "academic_writing"


def test_resolve_evidence_extract_execution_default():
    from backend.ai.capability_router.evidence_extract_resolve import resolve_evidence_extract_execution

    plan = resolve_evidence_extract_execution()
    assert plan.research_job.value == "evidence_extraction"
    assert plan.execution_policy.value == "lowest_cost"


def test_resolve_paper_analysis_execution_default():
    from backend.ai.capability_router.paper_analysis_resolve import resolve_paper_analysis_execution

    plan = resolve_paper_analysis_execution(quality_mode="balanced")
    assert plan.research_job.value == "analyze_paper"
    assert plan.capability.value == "scientific_reasoning"


def test_resolve_search_execution_default():
    from backend.ai.capability_router.search_resolve import resolve_search_execution

    plan = resolve_search_execution(quality_mode="balanced")
    assert plan.research_job.value == "search"
    assert plan.capability.value == "tool_use"
