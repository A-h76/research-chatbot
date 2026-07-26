"""Evidence Grading Engine — Phase 1.5.

Consumes backend.document_understanding.ProcessedDocument (Phase 1.1),
backend.classification.pass2.ClassificationResult (Phase 1.2),
backend.analysis_context.AnalysisContext (Phase 1.3), and backend.
medical_understanding.MedicalUnderstanding (Phase 1.4) and produces
EvidenceGrades — GRADE/Oxford CEBM/NIH/SIGN framework grades built on
seven shared prerequisite assessments (risk of bias, consistency,
precision, directness, publication bias, reporting quality,
applicability), aggregated with conflict resolution and a full audit
trail — see pipeline.py's module docstring for the full stage diagram.

Runs only when AnalysisContext's routing profile names "evidence_grading"
in its module_pipeline (CLINICAL_TRIAL, SYSTEMATIC_REVIEW); every other
document gets an EvidenceGrades with skipped=True and a clear reasoning
string, never a partial or fabricated grade.

Deliberately no module-level convenience function (matching every prior
phase's own __init__.py decision) — the Public API is exactly
EvidenceGradingPipeline.process(document, classification, context, medical),
already a one-liner.

Non-goals (see docstrings throughout this package): prompt generation,
knowledge graph construction, document classification, medical
understanding extraction, LLM integration, database/UI/API changes —
this package only grades evidence quality, using the same deterministic
rule-based approach as every phase before it. frameworks/usptf.py from
the task's own directory tree is deliberately not built (see enums.py's
module docstring for why).
"""

from .config import EvidenceGradingConfig
from .enums import (
    AggregationStrategy,
    BiasType,
    ConsistencyLevel,
    DirectnessLevel,
    ErrorSeverity,
    ErrorType,
    GradeType,
    GradingFramework,
    GRADEDowngradeFactor,
    GRADEQuality,
    GRADEUpgradeFactor,
    PrecisionLevel,
    RecommendationStrength,
    RecoveryType,
    RiskAssessmentTool,
    RiskLevel,
    StudyQuality,
)
from .models import (
    AggregationLog,
    ApplicabilityAssessment,
    AuditDecision,
    AuditTrail,
    ConfidenceInterval,
    ConfidenceScore,
    ConflictResolution,
    ConsistencyAssessment,
    DirectnessAssessment,
    EffectSize,
    EvidenceGrades,
    ExtractionError,
    FrameworkResult,
    Grade,
    GradeRationale,
    GRADEFrameworkResult,
    OutcomeGrade,
    PrecisionAssessment,
    PrerequisiteAssessments,
    PublicationBiasAssessment,
    RecoveryAction,
    ReportingQualityAssessment,
    RiskDomain,
    RiskOfBiasAssessment,
)
from .pipeline import EvidenceGradingPipeline

__all__ = [
    "EvidenceGradingPipeline",
    "EvidenceGradingConfig",
    # models
    "EvidenceGrades",
    "Grade",
    "GradeRationale",
    "RiskOfBiasAssessment",
    "RiskDomain",
    "ConsistencyAssessment",
    "PrecisionAssessment",
    "EffectSize",
    "ConfidenceInterval",
    "DirectnessAssessment",
    "PublicationBiasAssessment",
    "ReportingQualityAssessment",
    "ApplicabilityAssessment",
    "PrerequisiteAssessments",
    "GRADEFrameworkResult",
    "FrameworkResult",
    "OutcomeGrade",
    "ConflictResolution",
    "AggregationLog",
    "AuditDecision",
    "AuditTrail",
    "ConfidenceScore",
    "ExtractionError",
    "RecoveryAction",
    # enums
    "GradingFramework",
    "GradeType",
    "StudyQuality",
    "RiskLevel",
    "BiasType",
    "GRADEQuality",
    "RecommendationStrength",
    "RiskAssessmentTool",
    "ConsistencyLevel",
    "PrecisionLevel",
    "DirectnessLevel",
    "AggregationStrategy",
    "GRADEDowngradeFactor",
    "GRADEUpgradeFactor",
    "ErrorType",
    "ErrorSeverity",
    "RecoveryType",
]
