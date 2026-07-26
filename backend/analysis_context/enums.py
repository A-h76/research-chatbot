"""Closed label sets for the Analysis Context Engine.

No SectionType here — see package docstring's reuse table. Every field
in this package that needs one (SectionProfile.present_sections,
PromptProfile.section_priorities, ...) describes data that already comes
from backend.document_understanding.models.DocumentStructure
(normalized_headings, keyed by that package's own SectionType), so this
package imports and reuses that enum directly rather than defining a
second, differently-shaped one that every caller would have to
lossily convert between.

FallbackStrategy is this module's own addition, not part of the
originating task's literal Enums list (which used it on RoutingProfile.
fallback_strategy without ever defining it) — see routing_profile.py's
module docstring for what each member means and why.
"""

from enum import Enum


class AnalysisType(str, Enum):
    STATISTICAL_REVIEW = "statistical_review"
    BIAS_ASSESSMENT = "bias_assessment"
    METHODOLOGY_REVIEW = "methodology_review"
    CLINICAL_INTERPRETATION = "clinical_interpretation"
    DOMAIN_EXTRACTION = "domain_extraction"
    EVIDENCE_GRADING = "evidence_grading"
    CONSENSUS_DETECTION = "consensus_detection"
    GAP_ANALYSIS = "gap_analysis"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    UNKNOWN = "unknown"


class ReadinessLevel(str, Enum):
    FULLY_READY = "fully_ready"  # All recommended sections present
    PARTIALLY_READY = "partially_ready"  # Some recommended sections missing
    MINIMALLY_READY = "minimally_ready"  # Only a minority of recommended sections present
    NOT_READY = "not_ready"  # Critical sections missing
    UNKNOWN = "unknown"


class RoutingDecision(str, Enum):
    MEDICAL_FULL = "medical_full"  # Full medical pipeline
    MEDICAL_SCOPED = "medical_scoped"  # Scoped medical extraction
    SYSTEMATIC_REVIEW = "systematic_review"
    CLINICAL_TRIAL = "clinical_trial"
    COMPUTER_SCIENCE = "computer_science"
    MULTIDISCIPLINARY = "multidisciplinary"
    GENERIC = "generic"  # Generic document analysis
    UNKNOWN = "unknown"


class PromptFamily(str, Enum):
    MEDICAL = "medical"
    CLINICAL = "clinical"
    SYSTEMATIC = "systematic"
    METHODOLOGICAL = "methodological"
    COMPUTER_SCIENCE = "computer_science"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class PromptStrategy(str, Enum):
    SECTION_BASED = "section_based"
    CLAIM_BASED = "claim_based"
    EVIDENCE_BASED = "evidence_based"  # Phase 1.6 — high-confidence grades
    HYBRID = "hybrid"
    SUMMARY_FIRST = "summary_first"
    DETAILED_FIRST = "detailed_first"
    PICO_FIRST = "pico_first"  # Phase 1.6 — clinical trials / complete PICO


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"
    UNKNOWN = "unknown"


class AudienceType(str, Enum):
    CLINICAL = "clinical"
    RESEARCH = "research"
    PUBLIC = "public"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"
    MULTIDISCIPLINARY = "multidisciplinary"
    UNKNOWN = "unknown"


class FallbackStrategy(str, Enum):
    NONE = "none"  # Primary routing is confident; no fallback needed
    GENERIC_ANALYSIS = "generic_analysis"  # Fall back to domain-agnostic handling
    SKIP_OPTIONAL_MODULES = "skip_optional_modules"  # Run required_modules only
    MANUAL_REVIEW = "manual_review"  # Confidence too low to route automatically
