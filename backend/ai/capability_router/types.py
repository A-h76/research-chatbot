"""Capability Router vocabulary — v1.0 (ADR-0016).

Execution Profile = requirements · Execution Policy = constraints.
Names are capability-oriented, never model brands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ACR_VERSION = "1.0"
ACR_STATUS = "frozen_v1"


class ResearchJob(str, Enum):
    CHAT = "chat"
    ANALYZE_PAPER = "analyze_paper"
    COMPARE_PAPERS = "compare_papers"
    LITERATURE_REVIEW = "literature_review"
    REVIEWER = "reviewer"
    WRITING = "writing"
    SEARCH = "search"
    OCR = "ocr"
    EVIDENCE_EXTRACTION = "evidence_extraction"
    BULK_PROCESSING = "bulk_processing"


class Capability(str, Enum):
    SCIENTIFIC_REASONING = "scientific_reasoning"
    DEEP_SYNTHESIS = "deep_synthesis"
    ACADEMIC_WRITING = "academic_writing"
    LONG_CONTEXT = "long_context"
    VISION = "vision"
    CODE = "code"
    TRANSLATION = "translation"
    BULK_PROCESSING = "bulk_processing"
    STRUCTURED_EXTRACTION = "structured_extraction"
    TOOL_USE = "tool_use"


class ReasoningDepth(str, Enum):
    DEEP = "deep"
    STANDARD = "standard"
    LIGHT = "light"


class ContextNeed(str, Enum):
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class TemperatureBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ExecutionProfile:
    """Requirements for the job — not which model to use."""

    reasoning: ReasoningDepth = ReasoningDepth.STANDARD
    context: ContextNeed = ContextNeed.MEDIUM
    vision: bool = False
    structured_output: bool = False
    temperature: TemperatureBand = TemperatureBand.LOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning": self.reasoning.value,
            "context": self.context.value,
            "vision": self.vision,
            "structured_output": self.structured_output,
            "temperature": self.temperature.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ExecutionProfile:
        if not data:
            return cls()
        return cls(
            reasoning=ReasoningDepth(str(data.get("reasoning") or "standard")),
            context=ContextNeed(str(data.get("context") or "medium")),
            vision=bool(data.get("vision", False)),
            structured_output=bool(data.get("structured_output", False)),
            temperature=TemperatureBand(str(data.get("temperature") or "low")),
        )


class ExecutionPolicy(str, Enum):
    HIGHEST_QUALITY = "highest_quality"
    BALANCED = "balanced"
    LOWEST_COST = "lowest_cost"
    FASTEST = "fastest"
    OFFLINE = "offline"  # reserved
    ENTERPRISE_APPROVED = "enterprise_approved"  # reserved


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    MINIMAX = "minimax"
    GLM = "glm"


@dataclass(frozen=True)
class ExecutionPlan:
    """Resolved plan for one AI call (before/while invoking the gateway)."""

    research_job: ResearchJob
    capability: Capability
    execution_profile: ExecutionProfile
    execution_policy: ExecutionPolicy
    provider: Provider
    model: str
    prompt_name: str = ""  # Prompt Registry key hint
    router_version: str = ACR_VERSION
    notes: str = ""

    def to_provenance(
        self,
        *,
        tokens: int | None = None,
        cost_usd: float | None = None,
        duration_ms: int | None = None,
        prompt_version: str | None = None,
        execution_id: str | None = None,
    ) -> AIExecutionProvenance:
        return AIExecutionProvenance(
            research_job=self.research_job.value,
            capability=self.capability.value,
            execution_profile=self.execution_profile.to_dict(),
            execution_policy=self.execution_policy.value,
            provider=self.provider.value,
            model=self.model,
            tokens=tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            prompt_version=prompt_version or self.prompt_name or None,
            execution_id=execution_id,
            router_version=self.router_version,
        )


@dataclass
class AIExecutionProvenance:
    """Compact inspectable summary embedded on artifacts (ledger is SoR)."""

    research_job: str
    capability: str
    execution_policy: str
    provider: str
    model: str
    execution_profile: dict[str, Any] = field(default_factory=dict)
    tokens: int | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    prompt_version: str | None = None
    execution_id: str | None = None
    router_version: str = ACR_VERSION
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "research_job": self.research_job,
            "capability": self.capability,
            "execution_profile": self.execution_profile,
            "execution_policy": self.execution_policy,
            "provider": self.provider,
            "model": self.model,
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
            "duration_ms": self.duration_ms,
            "prompt_version": self.prompt_version,
            "execution_id": self.execution_id,
            "router_version": self.router_version,
        }
        if self.extra:
            payload["extra"] = self.extra
        return {"ai_execution": payload}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AIExecutionProvenance | None:
        if not data:
            return None
        block = data.get("ai_execution") if "ai_execution" in data else data
        if not isinstance(block, dict):
            return None
        required = ("research_job", "capability", "execution_policy", "provider", "model")
        if not all(block.get(k) for k in required):
            return None
        return cls(
            research_job=str(block["research_job"]),
            capability=str(block["capability"]),
            execution_policy=str(block["execution_policy"]),
            provider=str(block["provider"]),
            model=str(block["model"]),
            execution_profile=dict(block.get("execution_profile") or {}),
            tokens=block.get("tokens"),
            cost_usd=block.get("cost_usd"),
            duration_ms=block.get("duration_ms"),
            prompt_version=block.get("prompt_version"),
            execution_id=block.get("execution_id"),
            router_version=str(block.get("router_version") or ACR_VERSION),
            extra=dict(block.get("extra") or {}),
        )
