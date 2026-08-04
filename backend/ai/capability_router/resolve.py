"""resolve_execution — Research Job → Profile → Policy → Provider → Model (v1.0)."""

from __future__ import annotations

import logging
import os

from backend.ai.capability_router.profiles import JOB_DEFAULT_PROFILE, JOB_PROMPT_NAME
from backend.ai.capability_router.table import (
    JOB_CAPABILITY,
    JOB_DEFAULT_POLICY,
    ROUTE_TABLE,
    RouteTarget,
    _POLICY_FALLBACK,
)
from backend.ai.capability_router.types import (
    Capability,
    ExecutionPlan,
    ExecutionPolicy,
    ExecutionProfile,
    Provider,
    ResearchJob,
)

logger = logging.getLogger(__name__)

_TIER_A = frozenset({Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE})


def _parse_job(job: ResearchJob | str) -> ResearchJob:
    if isinstance(job, ResearchJob):
        return job
    return ResearchJob(str(job).strip().lower())


def _parse_policy(policy: ExecutionPolicy | str | None) -> ExecutionPolicy | None:
    if policy is None or policy == "":
        return None
    if isinstance(policy, ExecutionPolicy):
        return policy
    return ExecutionPolicy(str(policy).strip().lower())


def _parse_capability(cap: Capability | str | None) -> Capability | None:
    if cap is None or cap == "":
        return None
    if isinstance(cap, Capability):
        return cap
    return Capability(str(cap).strip().lower())


def _provider_available(provider: Provider) -> bool:
    if provider == Provider.OPENAI:
        return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_GATEWAY_API_KEY"))
    if provider == Provider.ANTHROPIC:
        if os.environ.get("ACR_REQUIRE_PROVIDER_KEYS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return bool(os.environ.get("ANTHROPIC_API_KEY"))
        return True
    if provider == Provider.GOOGLE:
        if os.environ.get("ACR_REQUIRE_PROVIDER_KEYS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
        return True
    return False


def _lookup_target(capability: Capability, policy: ExecutionPolicy):
    key = (capability, policy)
    if key in ROUTE_TABLE:
        return ROUTE_TABLE[key]
    for fb in _POLICY_FALLBACK:
        alt = (capability, fb)
        if alt in ROUTE_TABLE:
            return ROUTE_TABLE[alt]
    return RouteTarget(Provider.OPENAI, "gpt-5-mini", "fallback")


def _openai_fallback_model(policy: ExecutionPolicy) -> str:
    if policy == ExecutionPolicy.HIGHEST_QUALITY:
        return os.environ.get("ACR_MODEL_REASONING_HQ", "gpt-5.5-pro")
    if policy == ExecutionPolicy.BALANCED:
        return os.environ.get("ACR_MODEL_REASONING_BALANCED", "gpt-5.5")
    return "gpt-5-mini"


def _plan(
    *,
    job: ResearchJob,
    capability: Capability,
    profile: ExecutionProfile,
    policy: ExecutionPolicy,
    provider: Provider,
    model: str,
    notes: str = "",
) -> ExecutionPlan:
    return ExecutionPlan(
        research_job=job,
        capability=capability,
        execution_profile=profile,
        execution_policy=policy,
        provider=provider,
        model=model,
        prompt_name=JOB_PROMPT_NAME.get(job, ""),
        notes=notes,
    )


def resolve_execution(
    research_job: ResearchJob | str,
    *,
    execution_policy: ExecutionPolicy | str | None = None,
    execution_profile: ExecutionProfile | dict | None = None,
    capability_override: Capability | str | None = None,
    provider_override: Provider | str | None = None,
    model_override: str | None = None,
) -> ExecutionPlan:
    """Resolve Job → Profile → Policy → Provider → Model (ADR-0016 v1.0).

    Feature code must not pick providers/models in product UX by default.
    """
    job = _parse_job(research_job)
    capability = _parse_capability(capability_override) or JOB_CAPABILITY[job]
    policy = _parse_policy(execution_policy) or JOB_DEFAULT_POLICY.get(
        job, ExecutionPolicy.BALANCED
    )
    if isinstance(execution_profile, ExecutionProfile):
        profile = execution_profile
    elif isinstance(execution_profile, dict):
        profile = ExecutionProfile.from_dict(execution_profile)
    else:
        profile = JOB_DEFAULT_PROFILE.get(job, ExecutionProfile())

    if policy in (ExecutionPolicy.OFFLINE, ExecutionPolicy.ENTERPRISE_APPROVED):
        logger.info("acr reserved policy=%s → balanced", policy.value)
        policy = ExecutionPolicy.BALANCED

    if model_override and str(model_override).strip():
        prov = Provider.OPENAI
        if provider_override:
            prov = (
                provider_override
                if isinstance(provider_override, Provider)
                else Provider(str(provider_override).strip().lower())
            )
        return _plan(
            job=job,
            capability=capability,
            profile=profile,
            policy=policy,
            provider=prov,
            model=str(model_override).strip(),
            notes="model_override",
        )

    target = _lookup_target(capability, policy)

    if provider_override:
        prov = (
            provider_override
            if isinstance(provider_override, Provider)
            else Provider(str(provider_override).strip().lower())
        )
        if prov not in _TIER_A:
            raise ValueError(f"provider_not_tier_a:{prov.value}")
        if prov != target.provider and not model_override:
            rematch = None
            for (cap, pol), tgt in ROUTE_TABLE.items():
                if cap == capability and tgt.provider == prov:
                    rematch = tgt
                    if pol == policy:
                        break
            if rematch:
                target = rematch
            else:
                raise ValueError(f"no_route_for_provider:{prov.value}:{capability.value}")
        else:
            target = RouteTarget(prov, target.model, target.notes)

    if target.provider not in _TIER_A:
        raise ValueError(f"provider_not_tier_a:{target.provider.value}")

    if not _provider_available(target.provider) and target.provider != Provider.OPENAI:
        logger.info(
            "acr provider unavailable %s → openai fallback (job=%s)",
            target.provider.value,
            job.value,
        )
        return _plan(
            job=job,
            capability=capability,
            profile=profile,
            policy=policy,
            provider=Provider.OPENAI,
            model=_openai_fallback_model(policy),
            notes=f"fallback_from_{target.provider.value}",
        )

    return _plan(
        job=job,
        capability=capability,
        profile=profile,
        policy=policy,
        provider=target.provider,
        model=target.model,
        notes=target.notes,
    )


def legacy_gateway_task(research_job: ResearchJob | str) -> str:
    job = _parse_job(research_job)
    return {
        ResearchJob.CHAT: "chat",
        ResearchJob.ANALYZE_PAPER: "paper_analysis",
        ResearchJob.COMPARE_PAPERS: "paper_analysis",
        ResearchJob.LITERATURE_REVIEW: "literature_review",
        ResearchJob.REVIEWER: "reviewer",
        ResearchJob.WRITING: "section_generator",
        ResearchJob.SEARCH: "rag",
        ResearchJob.OCR: "paper_analysis",
        ResearchJob.EVIDENCE_EXTRACTION: "extract_metadata",
        ResearchJob.BULK_PROCESSING: "extract_metadata",
    }.get(job, "paper_analysis")


def legacy_quality_mode(policy: ExecutionPolicy | str | None) -> str:
    p = _parse_policy(policy) or ExecutionPolicy.BALANCED
    return {
        ExecutionPolicy.HIGHEST_QUALITY: "publication",
        ExecutionPolicy.BALANCED: "balanced",
        ExecutionPolicy.LOWEST_COST: "fast",
        ExecutionPolicy.FASTEST: "fast",
    }.get(p, "balanced")


def execution_policy_from_mode(mode: str | None) -> ExecutionPolicy:
    """Map legacy AI Gateway quality mode → Execution Policy."""
    m = (mode or "balanced").strip().lower()
    if m == "publication":
        return ExecutionPolicy.HIGHEST_QUALITY
    if m == "fast":
        return ExecutionPolicy.FASTEST
    return ExecutionPolicy.BALANCED
