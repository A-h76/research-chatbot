"""Configuration for the Prompt Assembly Engine."""

from dataclasses import dataclass, field

from backend.analysis_context.enums import PromptFamily, PromptStrategy

from .enums import TokenEstimationStrategy


@dataclass
class PromptAssemblyConfig:
    """See package docstring. Field names match the originating task
    with small hardening additions (default_temperature, critical
    component types that bypass the confidence filter)."""

    default_prompt_family: PromptFamily = PromptFamily.GENERIC
    default_strategy: PromptStrategy = PromptStrategy.SECTION_BASED
    default_temperature: float = 0.3

    max_system_prompt_tokens: int = 512
    max_user_prompt_tokens: int = 4096
    max_total_prompt_tokens: int = 4096

    confidence_threshold: float = 0.3
    high_confidence_threshold: float = 0.7
    evidence_threshold: float = 0.5

    include_evidence_with_confidence: bool = True
    include_low_confidence_entities: bool = False
    include_statistics: bool = True
    include_grading: bool = True
    include_pico: bool = True

    # Prefer Phase 1.3's already-computed prompt_profile when not UNKNOWN.
    prefer_context_prompt_profile: bool = True

    token_estimation_strategy: TokenEstimationStrategy = TokenEstimationStrategy.WORD_COUNT

    max_section_length: int = 5000
    max_abstract_length: int = 500
    max_evidence_per_claim: int = 3
    max_entities: int = 20

    output_format: str = "structured"  # "structured", "freeform", "hybrid"
    include_audit_trail: bool = True

    max_prompt_length: int = 10000
    sanitize_user_content: bool = True
    strip_html: bool = True

    enable_caching: bool = True
    cache_size: int = 50

    verbose_logging: bool = False

    # CRITICAL component types always survive confidence filtering.
    critical_component_types: list[str] = field(
        default_factory=lambda: [
            "system_instruction",
            "task_description",
            "document_context",
            "instruction",
            "output_format",
        ]
    )

    max_processing_time_ms: int = 15000
    max_components: int = 50
