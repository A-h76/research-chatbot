"""Closed label sets for the Medical Understanding Engine.

The four enums the originating task defined in full (ErrorType,
ErrorSeverity, RecoveryType, EntityNormalizationStatus) are reproduced
verbatim. The five domain-entity enums below (ClinicalEntityType,
InterventionType, OutcomeType, StatisticalMeasureType,
ClinicalRelationType) are this module's own addition — the task named
ClinicalEntityType as an explicit extension point ("New entity types via
ClinicalEntityType enum") without ever defining its members, and never
defined the other four at all despite every domain model in models.py
needing one. See models.py's own module docstring for the full list of
domain models designed from scratch for the same reason.

All members subclass `str` too (`class X(str, Enum)`), matching every
enum in backend.document_understanding/backend.classification/
backend.analysis_context — a value still serializes as its plain string
anywhere this app JSON-dumps a dataclass field.
"""

from enum import Enum

# ------------------------------------------------------------ given verbatim by the task


class ErrorType(str, Enum):
    VALIDATION_ERROR = "validation_error"
    EXTRACTION_ERROR = "extraction_error"
    NORMALIZATION_ERROR = "normalization_error"
    ONTOLOGY_LOOKUP_ERROR = "ontology_lookup_error"
    CONFIDENCE_ERROR = "confidence_error"
    TIMEOUT_ERROR = "timeout_error"
    MEMORY_LIMIT_ERROR = "memory_limit_error"
    REGEX_ERROR = "regex_error"
    PARSE_ERROR = "parse_error"


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"  # Pipeline must stop
    ERROR = "error"  # Module failed, can continue
    WARNING = "warning"  # Non-critical issue
    INFO = "info"  # Informational


class RecoveryType(str, Enum):
    ABSTRACT_FALLBACK = "abstract_fallback"
    TITLE_FALLBACK = "title_fallback"
    PATTERN_ALTERNATIVE = "pattern_alternative"
    DEDUPLICATION = "deduplication"
    NORMALIZATION = "normalization"
    INFERENCE = "inference"


class EntityNormalizationStatus(str, Enum):
    EXACT_MATCH = "exact_match"
    SYNONYM_MATCH = "synonym_match"
    FUZZY_MATCH = "fuzzy_match"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


# ------------------------------------------------------------ this module's own additions


class ClinicalEntityType(str, Enum):
    """The named extension point ("New entity types via ClinicalEntityType
    enum") — recognizing a new kind of clinical entity is adding a member
    here plus its keyword/synonym data in normalizers.py, nothing else."""

    CONDITION = "condition"
    DRUG = "drug"
    PROCEDURE = "procedure"
    SYMPTOM = "symptom"
    LAB_TEST = "lab_test"
    ANATOMICAL_SITE = "anatomical_site"
    DEVICE = "device"
    ADVERSE_EVENT = "adverse_event"
    BIOMARKER = "biomarker"
    OTHER = "other"


class InterventionType(str, Enum):
    DRUG = "drug"
    PROCEDURE = "procedure"
    DEVICE = "device"
    BEHAVIORAL = "behavioral"
    LIFESTYLE = "lifestyle"
    COMBINATION = "combination"
    OTHER = "other"


class OutcomeType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SAFETY = "safety"
    EXPLORATORY = "exploratory"
    OTHER = "other"


class StatisticalMeasureType(str, Enum):
    P_VALUE = "p_value"
    CONFIDENCE_INTERVAL = "confidence_interval"
    HAZARD_RATIO = "hazard_ratio"
    ODDS_RATIO = "odds_ratio"
    RELATIVE_RISK = "relative_risk"
    MEAN_DIFFERENCE = "mean_difference"
    STANDARD_DEVIATION = "standard_deviation"
    EFFECT_SIZE = "effect_size"
    OTHER = "other"


class ClinicalRelationType(str, Enum):
    TREATS = "treats"
    CAUSES = "causes"
    ASSOCIATED_WITH = "associated_with"
    CONTRAINDICATED_WITH = "contraindicated_with"
    MEASURED_BY = "measured_by"
    PART_OF = "part_of"
    OTHER = "other"
