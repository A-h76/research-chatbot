"""Dataclasses for the Prompt Assembly Engine.

Reuses: SectionType / EvidenceReference (Phase 1.1), PromptFamily /
PromptStrategy (Phase 1.3). ConfidenceScore and ExtractionError are
local (same per-phase pattern as 1.4/1.5).

Gaps filled vs the task's literal field list:
- PICOElements has no has_pico/evidence — builders derive completeness.
- EvidenceGrades has no evidence_references — builders collect from
  overall_grade.evidence and assessment evidence lists.
- PromptComponent.priority_level (PromptPriority) sits alongside the
  integer priority for CRITICAL bypass of the confidence filter.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from backend.analysis_context.enums import PromptFamily, PromptStrategy
from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import EvidenceReference

from .enums import ErrorSeverity, ErrorType, PromptComponentType, PromptPriority, RecoveryType


@dataclass
class ConfidenceScore:
    """Deterministic assembly confidence — mean of component confidences
    weighted by whether each was included."""

    overall: float
    components: dict[str, float]
    formula: str

    @staticmethod
    def calculate(
        component_mean: float,
        coverage: float,
        profile_confidence: float,
        sanitization_ok: float,
    ) -> "ConfidenceScore":
        overall = 0.40 * component_mean + 0.25 * coverage + 0.20 * profile_confidence + 0.15 * sanitization_ok
        return ConfidenceScore(
            overall=min(1.0, max(0.0, overall)),
            components={
                "component_mean": component_mean,
                "coverage": coverage,
                "profile_confidence": profile_confidence,
                "sanitization_ok": sanitization_ok,
            },
            formula=(
                "0.40*component_mean + 0.25*coverage + "
                "0.20*profile_confidence + 0.15*sanitization_ok"
            ),
        )

    @staticmethod
    def empty() -> "ConfidenceScore":
        return ConfidenceScore(overall=0.0, components={}, formula="")


@dataclass
class RecoveryAction:
    action_type: RecoveryType
    description: str
    success: bool
    fallback_value: Any = None


@dataclass
class ExtractionError:
    component: str
    error_type: ErrorType
    message: str
    severity: ErrorSeverity
    recovery_attempted: bool = False
    recovered: bool = False
    recovery_action: Optional[RecoveryAction] = None


@dataclass
class PromptComponent:
    component_type: PromptComponentType
    content: str
    priority: int
    confidence: float
    evidence: list[EvidenceReference] = field(default_factory=list)
    source: str = ""
    priority_level: PromptPriority = PromptPriority.MEDIUM


@dataclass
class DocumentContext:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    abstract: str = ""
    summary: Optional[str] = None
    key_sections: dict[SectionType, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssemblyDecision:
    decision_type: str
    rationale: str
    evidence: list[EvidenceReference] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AssemblyLog:
    decisions: list[AssemblyDecision] = field(default_factory=list)
    template_used: str = ""
    component_count: int = 0
    tokens_estimated: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_decision(
        self,
        decision_type: str,
        rationale: str,
        confidence: float = 1.0,
        evidence: Optional[list[EvidenceReference]] = None,
    ) -> None:
        self.decisions.append(
            AssemblyDecision(
                decision_type=decision_type,
                rationale=rationale,
                evidence=evidence or [],
                confidence=confidence,
            )
        )


@dataclass
class ConfidenceFilterResult:
    """Result of confidence-based component filtering."""

    threshold: float
    included_items: list[str] = field(default_factory=list)
    excluded_items: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class AssembledPrompt:
    """PromptAssemblyPipeline's final output."""

    system_prompt: str = ""
    user_prompt: str = ""
    full_prompt: str = ""
    components: list[PromptComponent] = field(default_factory=list)
    sections: dict[SectionType, str] = field(default_factory=dict)
    document_context: DocumentContext = field(default_factory=DocumentContext)
    evidence_included: list[EvidenceReference] = field(default_factory=list)
    confidence_score: ConfidenceScore = field(default_factory=ConfidenceScore.empty)
    prompt_family: PromptFamily = PromptFamily.GENERIC
    prompt_strategy: PromptStrategy = PromptStrategy.SECTION_BASED
    max_tokens: int = 4096
    temperature: float = 0.3
    assembly_log: AssemblyLog = field(default_factory=AssemblyLog)
    warnings: list[str] = field(default_factory=list)
    errors: list[ExtractionError] = field(default_factory=list)
    processing_time_ms: float = 0.0
    pipeline_version: str = ""
