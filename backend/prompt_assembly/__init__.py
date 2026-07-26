"""Prompt Assembly Engine — Phase 1.6.

Consumes ProcessedDocument (1.1), ClassificationResult (1.2),
AnalysisContext (1.3), MedicalUnderstanding (1.4), and EvidenceGrades
(1.5) and produces AssembledPrompt — structured system+user prompts
with priority-ordered components, confidence filtering, safe template
fill, and token clamping.

Design notes vs the originating task (applied during implementation):
- Reuse PromptFamily / PromptStrategy from analysis_context (extended
  with EVIDENCE_BASED and PICO_FIRST) rather than redefining them.
- Prefer context.prompt_profile when set; routing still overrides for
  CLINICAL_TRIAL / SYSTEMATIC_REVIEW templates.
- PICOElements has no has_pico — completeness is derived.
- EvidenceGrades has no evidence_references — evidence is collected from
  grade/assessment evidence lists.
- Templates never use str.format with document text (injection /
  KeyError risk); safe_fill_template + ContentSanitizer only.
- CRITICAL components always bypass the confidence filter.
- Always assembles (no skip path) — even when medical/grades are
  skipped — so downstream LLM clients always get a usable prompt.

Non-goals: LLM client calls, knowledge graph, DB/UI/API changes.
"""

from backend.analysis_context.enums import PromptFamily, PromptStrategy

from .config import PromptAssemblyConfig
from .enums import (
    ErrorSeverity,
    ErrorType,
    PromptComponentType,
    PromptPriority,
    RecoveryType,
    TokenEstimationStrategy,
)
from .models import (
    AssembledPrompt,
    AssemblyDecision,
    AssemblyLog,
    ConfidenceFilterResult,
    ConfidenceScore,
    DocumentContext,
    ExtractionError,
    PromptComponent,
    RecoveryAction,
)
from .pipeline import PromptAssemblyPipeline

__all__ = [
    "PromptAssemblyPipeline",
    "PromptAssemblyConfig",
    "AssembledPrompt",
    "PromptComponent",
    "DocumentContext",
    "AssemblyLog",
    "AssemblyDecision",
    "ConfidenceFilterResult",
    "ConfidenceScore",
    "ExtractionError",
    "RecoveryAction",
    "PromptFamily",
    "PromptStrategy",
    "PromptComponentType",
    "PromptPriority",
    "TokenEstimationStrategy",
    "ErrorType",
    "ErrorSeverity",
    "RecoveryType",
]
