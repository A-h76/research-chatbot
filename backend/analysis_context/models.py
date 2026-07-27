"""Dataclasses for the Analysis Context Engine.

Reuses rather than redefines: DocumentType/ScientificDomain/StudyDesign/
ReportingGuideline (backend.classification.pass2.enums — Phase 1.2's own
classification labels), SectionType (backend.document_understanding.
enums — Phase 1.1's section taxonomy, since present_sections/
section_priorities/etc. describe exactly the data already keyed by it in
DocumentStructure.normalized_headings), EvidenceReference
(backend.document_understanding.models — Phase 1.1's own traceability
shape) and QualityLevel (backend.document_understanding.enums, for
AnalysisQualityProfile.reliability_level below). See package docstring
for the full reuse rationale.

Two types referenced by the originating task's own field list but never
defined anywhere in it — ConfidenceScore (on AnalysisContext.confidence)
and AnalysisQualityProfile (on AnalysisContext.quality_profile, and only
present at all because the task's own directory tree names a
quality_profile.py file the task's Models section never backs with a
class) — are defined here to fill that gap; see each one's own docstring
for the reasoning.
"""

from dataclasses import dataclass, field
from typing import Optional

from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from backend.document_understanding.enums import QualityLevel, SectionType
from backend.document_understanding.models import EvidenceReference

from .enums import (
    AnalysisType,
    AudienceType,
    ComplexityLevel,
    FallbackStrategy,
    PromptFamily,
    PromptStrategy,
    ReadinessLevel,
    RoutingDecision,
)

# ------------------------------------------------------------ document_profile.py's output


@dataclass
class DocumentProfile:
    """A document-level summary for downstream orchestration — see
    document_profile.py. document_type/domain/study_design/
    reporting_guideline are read straight from ClassificationResult, not
    re-derived; intended_audience/complexity_level are this package's own
    new inferences (see document_profile.py)."""

    document_type: DocumentType
    domain: ScientificDomain
    study_design: StudyDesign
    reporting_guideline: Optional[ReportingGuideline]
    intended_audience: AudienceType
    complexity_level: ComplexityLevel
    confidence: float
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class AnalysisProfile:
    """Which kinds of downstream analysis this document supports, and
    whether it's ready for them — see analysis_profile.py."""

    analysis_types: list[AnalysisType] = field(default_factory=list)
    required_modules: list[str] = field(default_factory=list)
    suggested_modules: list[str] = field(default_factory=list)
    readiness_score: float = 0.0
    readiness_level: ReadinessLevel = ReadinessLevel.UNKNOWN
    limitations: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class SectionProfile:
    """Section-level completeness assessment — see section_profile.py.
    Keyed by backend.document_understanding.enums.SectionType throughout
    (see module docstring)."""

    present_sections: list[SectionType] = field(default_factory=list)
    missing_sections: list[SectionType] = field(default_factory=list)
    section_completeness: dict[SectionType, float] = field(default_factory=dict)
    section_confidence: dict[SectionType, float] = field(default_factory=dict)
    recommended_sections: list[SectionType] = field(default_factory=list)
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class RoutingProfile:
    """Which downstream module pipeline this document should be routed
    through — see routing_profile.py."""

    primary_routing: RoutingDecision
    secondary_routing: list[RoutingDecision] = field(default_factory=list)
    module_pipeline: list[str] = field(default_factory=list)
    fallback_strategy: FallbackStrategy = FallbackStrategy.NONE
    priority_weights: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class EvidencePriorities:
    """How downstream evidence selection should be scoped — see
    prompt_profile.py. priority_claims is always empty in this phase
    (see prompt_profile.py's module docstring: claim-level extraction is
    a Non-Goal, deferred to a later phase) — the field exists now so a
    later phase populating it is a field assignment, not a new field."""

    priority_sections: list[SectionType] = field(default_factory=list)
    priority_claims: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.0
    max_evidence_per_claim: int = 0
    require_primary_sources: bool = False


@dataclass
class PromptProfile:
    """Prompt strategy determination — see prompt_profile.py."""

    prompt_family: PromptFamily
    prompt_strategy: PromptStrategy
    section_priorities: list[SectionType] = field(default_factory=list)
    key_themes: list[str] = field(default_factory=list)
    evidence_priorities: EvidencePriorities = field(default_factory=EvidencePriorities)
    confidence: float = 0.0


@dataclass
class AnalysisQualityProfile:
    """How much AnalysisContext's own conclusions can be trusted, given
    the quality of its two inputs — see quality_profile.py. Distinct from
    ConfidenceScore below: this is about input reliability (was the
    source document clean, was classification confident at all), not
    about how confident each of *this* package's own profiles are in
    their own conclusions."""

    input_document_quality: float = 0.0
    input_classification_confidence: float = 0.0
    reliability_score: float = 0.0
    reliability_level: QualityLevel = QualityLevel.UNUSABLE
    caveats: list[str] = field(default_factory=list)


@dataclass
class ConfidenceScore:
    """Aggregated confidence across this package's five profiles — see
    confidence.py. `overall` is a plain mean of the five breakdown
    fields, the same "transparent aggregate, not a re-weighted hidden
    recombination" choice backend.classification.pass1's own
    classify_document() and backend.document_understanding's DocumentQuality
    both already make."""

    overall: float
    document_profile: float
    section_profile: float
    analysis_profile: float
    routing_profile: float
    prompt_profile: float


@dataclass
class AnalysisContext:
    """AnalysisContextPipeline's final output for one (ProcessedDocument,
    ClassificationResult) pair — a roadmap for downstream phases, not an
    extraction of domain-specific facts (see package docstring's
    Non-Goals)."""

    document_profile: DocumentProfile
    analysis_profile: AnalysisProfile
    section_profile: SectionProfile
    routing_profile: RoutingProfile
    prompt_profile: PromptProfile
    quality_profile: AnalysisQualityProfile
    confidence: ConfidenceScore
    warnings: list[str]
    processing_time_ms: float
    pipeline_version: str
