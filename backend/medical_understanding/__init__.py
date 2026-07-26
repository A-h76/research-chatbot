"""Medical Understanding Engine — Phase 1.4.

Consumes backend.document_understanding.ProcessedDocument (Phase 1.1),
backend.classification.pass2.ClassificationResult (Phase 1.2), and
backend.analysis_context.AnalysisContext (Phase 1.3) and extracts
clinical entities, PICO elements, study characteristics, interventions,
populations, outcomes, statistical measures, and temporal data from
medical/clinical documents — see pipeline.py's module docstring for the
full stage diagram.

Runs only when AnalysisContext's routing profile indicates a medical/
clinical document (MEDICAL_FULL, MEDICAL_SCOPED, CLINICAL_TRIAL,
SYSTEMATIC_REVIEW); every other document gets a MedicalUnderstanding
with skipped=True and a clear reasoning string, never a partial or
fabricated extraction.

Deliberately no module-level convenience function (matching every prior
phase's own __init__.py decision) — the Public API is exactly
MedicalUnderstandingPipeline.process(document, classification, context),
already a one-liner.

Non-goals (see docstrings throughout this package): evidence grading
(PICO/GRADE), prompt generation, knowledge graph construction, database
persistence changes, UI changes, API endpoint changes, LLM integration —
this package only extracts, using the same deterministic keyword/regex
approach as every phase before it.
"""

from .config import MedicalUnderstandingConfig
from .enums import (
    ClinicalEntityType,
    ClinicalRelationType,
    EntityNormalizationStatus,
    ErrorSeverity,
    ErrorType,
    InterventionType,
    OutcomeType,
    RecoveryType,
    StatisticalMeasureType,
)
from .models import (
    ClinicalEntity,
    ClinicalRelation,
    Comparator,
    ConfidenceScore,
    DemographicData,
    ExtractionError,
    ExtractionSummary,
    Intervention,
    KeyFinding,
    MedicalUnderstanding,
    Outcome,
    PICOElements,
    Population,
    RecoveryAction,
    StatisticalMeasure,
    StudyCharacteristics,
    TemporalData,
)
from .pipeline import MedicalUnderstandingPipeline

__all__ = [
    "MedicalUnderstandingPipeline",
    "MedicalUnderstandingConfig",
    # models
    "MedicalUnderstanding",
    "ClinicalEntity",
    "ClinicalRelation",
    "Population",
    "Intervention",
    "Comparator",
    "Outcome",
    "StatisticalMeasure",
    "TemporalData",
    "DemographicData",
    "StudyCharacteristics",
    "KeyFinding",
    "PICOElements",
    "ConfidenceScore",
    "ExtractionSummary",
    "ExtractionError",
    "RecoveryAction",
    # enums
    "ClinicalEntityType",
    "InterventionType",
    "OutcomeType",
    "StatisticalMeasureType",
    "ClinicalRelationType",
    "ErrorType",
    "ErrorSeverity",
    "RecoveryType",
    "EntityNormalizationStatus",
]
