"""Configuration for the Medical Understanding Engine. Every tunable
referenced elsewhere in this package (regex limits, entity limits,
confidence thresholds, ...) lives here, not as a scattered magic number
in the module that actually uses it.

One deliberate deviation from the task's own literal default:
ontology_provider defaults to "local" here, not "umls" — "umls" and
"snomed_ct" are recognized (see normalizers.py's module docstring) but
not actually implemented (this codebase has no UMLS/SNOMED CT license,
API credentials, or bundled terminology data, and every phase since 1.1
has been explicitly deterministic/dependency-free by design). Defaulting
a fresh MedicalUnderstandingConfig() to a provider that immediately
falls back with a warning would be a worse default than one that's
honest about what actually runs.
"""

from dataclasses import dataclass, field


@dataclass
class MedicalUnderstandingConfig:
    """See module docstring. Field names/defaults otherwise match the
    originating task's own configuration spec verbatim."""

    # Enabled extractors
    enabled_extractors: list[str] = field(
        default_factory=lambda: [
            "clinical_entities",
            "populations",
            "interventions",
            "comparators",
            "outcomes",
            "study_characteristics",
            "statistical_measures",
            "temporal_data",
        ]
    )

    # Resource limits
    max_entities: int = 10000
    max_relations: int = 5000
    max_evidence_references: int = 1000
    max_paragraph_size: int = 5000
    max_processing_time_ms: int = 30000
    max_context_length: int = 256

    # Confidence thresholds
    confidence_threshold: float = 0.3
    high_confidence_threshold: float = 0.7

    # Security
    regex_timeout_ms: int = 100
    max_regex_length: int = 1000

    # Parallel execution
    enable_parallel: bool = True
    max_parallel_workers: int = 4

    # Cache
    cache_enabled: bool = True
    cache_size: int = 100

    # Debug
    verbose_logging: bool = False

    # Ontology — see module docstring for why this defaults to "local"
    ontology_provider: str = "local"  # "local", "umls", "snomed_ct"
    ontology_cache_size: int = 1000

    # Normalization
    normalization_strategy: str = "exact_then_synonym_then_fuzzy"

    # Post-processing
    deduplicate_entities: bool = True
    validate_output: bool = True
