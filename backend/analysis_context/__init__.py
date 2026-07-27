"""Analysis Context Engine — Phase 1.3.

Consumes backend.document_understanding.ProcessedDocument (Phase 1.1)
and backend.classification.pass2.ClassificationResult (Phase 1.2) and
produces one AnalysisContext: a domain-agnostic roadmap for downstream
phases (routing decisions, module selection, section completeness,
prompt strategy, evidence prioritization) — see pipeline.py's module
docstring for the full stage diagram.

Deliberately no module-level convenience function (matching Phase 1.1's
and Phase 1.2's own __init__.py decisions) — the Public API is exactly
AnalysisContextPipeline.process(document, classification), already a
one-liner.

Non-goals (see docstrings throughout this package): clinical entity
extraction, PICO extraction, study-characteristic extraction beyond what
classification already provides, domain-specific medical extraction,
evidence grading, prompt generation, LLM integration — this package only
orchestrates a roadmap, using the same deterministic rule-based approach
as Phase 1.1 and Phase 1.2.
"""

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
from .models import (
    AnalysisContext,
    AnalysisProfile,
    AnalysisQualityProfile,
    ConfidenceScore,
    DocumentProfile,
    EvidencePriorities,
    PromptProfile,
    RoutingProfile,
    SectionProfile,
)
from .pipeline import AnalysisContextPipeline

__all__ = [
    "AnalysisContextPipeline",
    # models
    "AnalysisContext",
    "DocumentProfile",
    "AnalysisProfile",
    "SectionProfile",
    "RoutingProfile",
    "PromptProfile",
    "EvidencePriorities",
    "AnalysisQualityProfile",
    "ConfidenceScore",
    # enums
    "AnalysisType",
    "ReadinessLevel",
    "RoutingDecision",
    "PromptFamily",
    "PromptStrategy",
    "ComplexityLevel",
    "AudienceType",
    "FallbackStrategy",
]
