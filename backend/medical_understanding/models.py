"""Dataclasses for the Medical Understanding Engine.

The task gave full field-level detail for the *meta* layer
(MedicalUnderstanding, ExtractionSummary, ConfidenceScore, ExtractionError,
RecoveryAction) but never defined a single field for the actual clinical
content types every one of those meta-models references: ClinicalEntity,
PICOElements, StudyCharacteristics, Intervention, Population, Comparator,
Outcome, StatisticalMeasure, TemporalData, DemographicData, KeyFinding,
plus ClinicalRelation (needed by entity_registry.py's EntityRegistry.
relations). All eleven are designed from scratch here, evidence-linked
via backend.document_understanding.models.EvidenceReference throughout
(the task's own "Reuse from Phase 1.1: EvidenceReference" principle) —
every extracted fact points back to where in the source document it came
from, the same discipline every phase since 1.1 has followed.

Every domain model's numeric/free-text fields (dosage, blinding method,
age range, ...) are kept as plain strings rather than parsed into
structured sub-fields — real medical papers report these in wildly
inconsistent formats, and parsing "18-65 years" vs "aged 18 to 65" vs
"mean age 42.3" into one structured shape is a much bigger, separate
effort than this phase's deterministic keyword/regex extraction can
honestly support. Every field defaults to None/empty rather than being
required, since any single fact may legitimately not be found in a given
document — see each extractor's own module docstring for what's realistic
to expect.

DocumentIndex's own supporting types (Paragraph, Table, Figure, Reference,
TextMatch) live in document_index.py, not here — they're input-side
plumbing this pipeline consumes, not part of MedicalUnderstanding's own
output shape.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.classification.pass2.enums import StudyDesign
from backend.document_understanding.models import EvidenceReference

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

# ------------------------------------------------------------ domain entities (this module's own design)


@dataclass
class ClinicalEntity:
    """One clinical concept found in the text — see extractors/
    clinical_entities.py."""

    value: str
    entity_type: ClinicalEntityType
    raw_text: str
    normalization_status: EntityNormalizationStatus
    confidence: float
    evidence: EvidenceReference
    synonyms: list[str] = field(default_factory=list)


@dataclass
class Population:
    """The studied population — see extractors/populations.py."""

    description: str = ""
    sample_size: Optional[int] = None
    inclusion_criteria: list[str] = field(default_factory=list)
    exclusion_criteria: list[str] = field(default_factory=list)
    age_range: Optional[str] = None
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class Intervention:
    """One studied intervention — see extractors/interventions.py."""

    name: str
    intervention_type: InterventionType = InterventionType.OTHER
    dosage: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class Comparator:
    """What an intervention was compared against — see extractors/
    comparators.py. A distinct model from Intervention (not reused for
    it) because PICO treats "what was studied" and "what it was compared
    against" as separate roles even when both are, mechanically, drugs or
    procedures — is_placebo/is_active_control capture that role directly
    rather than forcing callers to infer it from intervention_type."""

    name: str
    is_placebo: bool = False
    is_active_control: bool = False
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class Outcome:
    """One measured outcome — see extractors/outcomes.py."""

    name: str
    outcome_type: OutcomeType = OutcomeType.OTHER
    measurement_method: Optional[str] = None
    time_point: Optional[str] = None
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class StatisticalMeasure:
    """One reported statistical measure — see extractors/
    statistical_measures.py. `value` is kept as the raw matched text
    (e.g. "1.45 (95% CI 1.02-2.07)") rather than parsed into separate
    point-estimate/interval fields — see module docstring."""

    measure_type: StatisticalMeasureType
    value: str
    associated_outcome: Optional[str] = None
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class TemporalData:
    """Study timing facts — see extractors/temporal_data.py."""

    study_duration: Optional[str] = None
    follow_up_period: Optional[str] = None
    enrollment_period: Optional[str] = None
    key_timepoints: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class DemographicData:
    """Participant demographics — see extractors/populations.py (which
    populates both Population and DemographicData from the same
    signals)."""

    total_participants: Optional[int] = None
    mean_age: Optional[str] = None
    sex_distribution: Optional[str] = None
    ethnicity_data: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class StudyCharacteristics:
    """Study-design-level facts beyond what classification already
    provides (see package docstring's Non-Goals: "Study characteristic
    extraction beyond what classification provides" is explicitly in
    scope here, one phase later than backend.analysis_context's own
    identical Non-Goal wording) — see extractors/study_characteristics.py.
    study_design is backend.classification.pass2.enums.StudyDesign,
    reused directly (see package docstring's "Reuse from Phase 1.2")."""

    study_design: StudyDesign = StudyDesign.UNKNOWN
    number_of_arms: Optional[int] = None
    blinding: Optional[str] = None
    randomization_method: Optional[str] = None
    multicenter: Optional[bool] = None
    number_of_sites: Optional[int] = None
    confidence: float = 0.0
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class KeyFinding:
    """One notable result statement — see extractors/outcomes.py."""

    statement: str
    supporting_outcome: Optional[str] = None
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


@dataclass
class PICOElements:
    """Population/Intervention/Comparator/Outcome, assembled from the
    already-extracted lists above — see pico_builder.py. Not a new
    extraction pass: every field here is a reference to (or the first/
    primary entry from) the corresponding list already produced by
    populations.py/interventions.py/comparators.py/outcomes.py."""

    population: Optional[Population] = None
    interventions: list[Intervention] = field(default_factory=list)
    comparators: list[Comparator] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ClinicalRelation:
    """One relation between two clinical entities (by their normalized
    value, not object identity — see entity_registry.py) — e.g. drug X
    TREATS condition Y. subject/object are EntityRegistry keys, not
    ClinicalEntity objects, so a relation survives independently of
    whichever entity object instance produced it."""

    subject: str
    relation_type: ClinicalRelationType
    object: str
    confidence: float = 0.0
    evidence: Optional[EvidenceReference] = None


# ------------------------------------------------------------ meta-models (given by the task, verbatim shape)


@dataclass
class RecoveryAction:
    action_type: RecoveryType
    description: str
    success: bool
    fallback_value: Any = None


@dataclass
class ExtractionError:
    extractor: str
    error_type: ErrorType
    message: str
    severity: ErrorSeverity
    recovery_attempted: bool = False
    recovered: bool = False
    recovery_action: Optional[RecoveryAction] = None


@dataclass
class ConfidenceScore:
    """Deterministic, explainable confidence — see confidence.py's
    module docstring for how the four components are actually computed
    from real extraction data before calling calculate()."""

    overall: float
    components: dict[str, float]
    formula: str

    @staticmethod
    def calculate(
        section_quality: float,
        evidence_count: float,
        keyword_confidence: float,
        normalization_quality: float,
    ) -> "ConfidenceScore":
        overall = 0.4 * section_quality + 0.3 * evidence_count + 0.2 * keyword_confidence + 0.1 * normalization_quality
        return ConfidenceScore(
            overall=min(1.0, max(0.0, overall)),
            components={
                "section_quality": section_quality,
                "evidence_count": evidence_count,
                "keyword_confidence": keyword_confidence,
                "normalization_quality": normalization_quality,
            },
            formula="0.4*section_quality + 0.3*evidence_count + 0.2*keyword_confidence + 0.1*normalization_quality",
        )

    @staticmethod
    def empty() -> "ConfidenceScore":
        return ConfidenceScore(overall=0.0, components={}, formula="")


@dataclass
class ExtractionSummary:
    enabled_extractors: list[str] = field(default_factory=list)
    executed_extractors: list[str] = field(default_factory=list)
    skipped_extractors: list[str] = field(default_factory=list)
    failed_extractors: list[str] = field(default_factory=list)
    entity_counts: dict[str, int] = field(default_factory=dict)
    total_entities: int = 0
    partial_success: bool = False
    overall_success_rate: float = 0.0


@dataclass
class MedicalUnderstanding:
    """MedicalUnderstandingPipeline's final output — see pipeline.py.

    Every field beyond skipped/reasoning defaults to an empty/neutral
    value so the `skipped=True` fast path (a non-medical document) can
    construct one with just those two kwargs, exactly as the task's own
    pipeline.py pseudocode does."""

    skipped: bool = False
    reasoning: Optional[str] = None
    clinical_entities: list[ClinicalEntity] = field(default_factory=list)
    pico_elements: Optional[PICOElements] = None
    study_characteristics: Optional[StudyCharacteristics] = None
    interventions: list[Intervention] = field(default_factory=list)
    populations: list[Population] = field(default_factory=list)
    comparators: list[Comparator] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    statistical_measures: list[StatisticalMeasure] = field(default_factory=list)
    temporal_data: Optional[TemporalData] = None
    demographic_data: Optional[DemographicData] = None
    key_findings: list[KeyFinding] = field(default_factory=list)
    extraction_summary: ExtractionSummary = field(default_factory=ExtractionSummary)
    confidence: ConfidenceScore = field(default_factory=ConfidenceScore.empty)
    errors: list[ExtractionError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recoveries: list[RecoveryAction] = field(default_factory=list)
    processing_time_ms: float = 0.0
    pipeline_version: str = ""
