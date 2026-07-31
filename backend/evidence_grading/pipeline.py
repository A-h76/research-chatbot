"""EvidenceGradingPipeline — the package's one public entry point.

    (ProcessedDocument, ClassificationResult, AnalysisContext, MedicalUnderstanding)
        |
        v
    Routing check         (_should_run)   -- skip entirely unless routing_profile.
                                              module_pipeline names "evidence_grading"
        |
        v
    GraderRegistry.execute_dag()           -- prerequisite assessors (tiered), then
                                              framework graders (tiered); every grader
                                              consumes the SAME shared PrerequisiteAssessments
                                              (steps 2-3 of the task's own pseudocode — one
                                              call, since assessors must finish before any
                                              grader can consume them)
        |
        v
    Grade aggregation      (aggregators/grade_aggregator.py)  -- folds in conflict
                                              detection/resolution (step 4-5)
    Outcome aggregation    (aggregators/outcome_aggregator.py)
        |
        v
    Confidence             (confidence.py)
    Audit trail             (audit.py)      -- one record per GRADE downgrade/upgrade
                                              factor, one per conflict, one for aggregation
        |
        v
    EvidenceGrades          (models.py)     -- step 6

Graceful degradation: registry.execute_dag() already isolates each
assessor/grader's own crash (registry.py's _safe_call, itself routed
through security/isolation.py's PluginIsolator); this module's own
_run_stage() wraps aggregation/outcome-assembly/confidence the same way
every prior phase's pipeline.py does, so a bug there degrades to a
warning, never an unhandled exception. process() itself only raises for
the one caller-bug case (wrong argument types — see validators.py).
"""

import time
from typing import Callable, Optional, TypeVar

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from .aggregators.conflict_resolver import agreement_score
from .aggregators.grade_aggregator import aggregate_grade
from .aggregators.outcome_aggregator import aggregate_outcomes
from .assessments.applicability import ApplicabilityAssessor
from .assessments.consistency import ConsistencyAssessor
from .assessments.directness import DirectnessAssessor
from .assessments.precision import PrecisionAssessor
from .assessments.publication_bias import PublicationBiasAssessor
from .assessments.reporting_quality import ReportingQualityAssessor
from .assessments.risk_of_bias import RiskOfBiasAssessor
from .audit import record_aggregation, record_conflict_resolution, record_downgrade, record_upgrade
from .confidence import compute_confidence
from .config import EvidenceGradingConfig
from .enums import GradingFramework, StudyQuality
from .frameworks.grade import GRADEGrader
from .frameworks.nih import NIHGrader
from .frameworks.oxford import OxfordGrader
from .frameworks.sign import SIGNGrader
from .models import AggregationLog, AuditTrail, ConfidenceScore, EvidenceGrades, FrameworkResult, OutcomeGrade
from .registry import GraderRegistry
from .security.limits import ResourceGuard
from .security.sanitizers import Sanitizer
from .validators import require_valid_inputs, validate_inputs, validate_output

PIPELINE_VERSION = "1.0.0"

_Result = TypeVar("_Result")


class EvidenceGradingPipeline:
    """See module docstring. config controls which frameworks/assessments
    are enabled, aggregation strategy, resource limits, and parallel
    execution — see config.py."""

    def __init__(self, config: Optional[EvidenceGradingConfig] = None) -> None:
        self.config = config or EvidenceGradingConfig()
        self.registry = GraderRegistry(self.config)
        self._register_default_graders()

    def _register_default_graders(self) -> None:
        self.registry.register_prerequisite_assessor("risk_of_bias", RiskOfBiasAssessor())
        self.registry.register_prerequisite_assessor("consistency", ConsistencyAssessor(self.config))
        self.registry.register_prerequisite_assessor("precision", PrecisionAssessor())
        self.registry.register_prerequisite_assessor("directness", DirectnessAssessor())
        self.registry.register_prerequisite_assessor("publication_bias", PublicationBiasAssessor(self.config))
        self.registry.register_prerequisite_assessor("reporting_quality", ReportingQualityAssessor())
        self.registry.register_prerequisite_assessor("applicability", ApplicabilityAssessor())

        self.registry.register_framework_grader("grade", GRADEGrader(self.config))
        self.registry.register_framework_grader("oxford", OxfordGrader())
        self.registry.register_framework_grader("nih", NIHGrader())
        self.registry.register_framework_grader("sign", SIGNGrader())

    def process(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
    ) -> EvidenceGrades:
        require_valid_inputs(document, classification, context, medical)
        start = time.perf_counter()

        if not self._should_run(context):
            return EvidenceGrades(
                skipped=True,
                reasoning=(
                    "Formal evidence grading was not run for this document type. "
                    "Common for narrative reviews, editorials, and papers outside "
                    "clinical-trial or systematic-review pipelines."
                ),
                pipeline_version=PIPELINE_VERSION,
                processing_time_ms=(time.perf_counter() - start) * 1000,
            )

        warnings = validate_inputs(document, classification, medical)

        plan = self.registry.get_assessment_plan(context)
        prerequisites, results_by_name, dag_errors = self.registry.execute_dag(plan, document, classification, medical)
        framework_results = self._key_by_framework(results_by_name)

        aggregation_log = self._run_stage(
            "aggregation",
            lambda: aggregate_grade(framework_results, self.config),
            AggregationLog(),
            warnings,
        )

        outcome_grades: dict[str, OutcomeGrade] = self._run_stage(
            "outcome_aggregation",
            lambda: aggregate_outcomes(medical, aggregation_log.final_grade),
            {},
            warnings,
        )

        confidence = self._run_stage(
            "confidence",
            lambda: compute_confidence(
                prerequisites,
                enabled_framework_count=len(plan.enabled_graders),
                produced_framework_count=len(framework_results),
                assessment_agreement=agreement_score(framework_results),
                medical_confidence=medical.confidence.overall,
            ),
            ConfidenceScore.empty(),
            warnings,
        )

        audit_trail = AuditTrail()
        if self.config.enable_audit_trail:
            self._record_audit(audit_trail, framework_results, aggregation_log)
            self._sanitize_audit_trail(audit_trail)

        guard = ResourceGuard(self.config)
        if len(outcome_grades) > guard.max_outcomes:
            outcome_grades = dict(list(outcome_grades.items())[: guard.max_outcomes])
        aggregation_log.final_grade.evidence = guard.clamp_evidence(aggregation_log.final_grade.evidence)
        aggregation_log.final_grade.rationale = guard.clamp_rationale(aggregation_log.final_grade.rationale)
        self._sanitize_grade_text(aggregation_log.final_grade)

        processing_time_ms = (time.perf_counter() - start) * 1000
        if processing_time_ms > self.config.max_processing_time_ms:
            warnings.append(
                f"processing exceeded max_processing_time_ms "
                f"({processing_time_ms:.0f}ms > {self.config.max_processing_time_ms}ms)"
            )

        grades = EvidenceGrades(
            skipped=False,
            reasoning=None,
            overall_grade=aggregation_log.final_grade,
            study_quality=self._study_quality(aggregation_log.final_grade.grade_value),
            risk_of_bias=prerequisites.risk_of_bias,
            consistency=prerequisites.consistency,
            precision=prerequisites.precision,
            directness=prerequisites.directness,
            publication_bias=prerequisites.publication_bias,
            reporting_quality=prerequisites.reporting_quality,
            outcome_grades=outcome_grades,
            framework_results=framework_results,
            aggregation_log=aggregation_log,
            audit_trail=audit_trail,
            confidence=confidence,
            warnings=warnings,
            errors=dag_errors,
            processing_time_ms=processing_time_ms,
            pipeline_version=PIPELINE_VERSION,
        )

        grades.warnings.extend(validate_output(grades, self.config))
        return grades

    @staticmethod
    def _should_run(context: AnalysisContext) -> bool:
        return "evidence_grading" in context.routing_profile.module_pipeline

    @staticmethod
    def _key_by_framework(results_by_name: dict[str, FrameworkResult]) -> dict[GradingFramework, FrameworkResult]:
        return {result.framework: result for result in results_by_name.values() if result is not None}

    @staticmethod
    def _study_quality(grade_value: str) -> StudyQuality:
        try:
            return StudyQuality(grade_value)
        except ValueError:
            return StudyQuality.UNKNOWN

    def _sanitize_grade_text(self, grade) -> None:
        """Apply HTML/markdown sanitization to user-facing rationale and
        description strings before they leave the pipeline."""
        sanitizer = Sanitizer(self.config.max_rationale_length)
        grade.grade_description = sanitizer.sanitize_rationale(grade.grade_description or "")
        for entry in grade.rationale:
            entry.reasoning = sanitizer.sanitize_rationale(entry.reasoning or "")

    def _sanitize_audit_trail(self, trail: AuditTrail) -> None:
        sanitizer = Sanitizer(self.config.max_rationale_length)
        for decision in trail.decisions:
            decision.reasoning = sanitizer.sanitize_rationale(decision.reasoning or "")
            decision.result = sanitizer.sanitize_rationale(decision.result or "")
            decision.rule = sanitizer.sanitize_rationale(decision.rule or "")

    @staticmethod
    def _record_audit(trail: AuditTrail, framework_results: dict, aggregation_log: AggregationLog) -> None:
        grade_result = framework_results.get(GradingFramework.GRADE)
        if grade_result is not None and grade_result.grade_result is not None:
            for factor in grade_result.grade_result.downgrade_factors:
                record_downgrade(trail, GradingFramework.GRADE, factor.value, 1, grade_result.evidence)
            for factor in grade_result.grade_result.upgrade_factors:
                record_upgrade(trail, GradingFramework.GRADE, factor.value, 1, grade_result.evidence)

        for conflict in aggregation_log.conflict_resolution_log:
            record_conflict_resolution(trail, conflict.resolution_strategy, conflict.resolved_value, [])

        record_aggregation(
            trail,
            aggregation_log.aggregation_strategy.value,
            aggregation_log.final_grade.grade_value,
            aggregation_log.final_grade.evidence,
        )

    @staticmethod
    def _run_stage(name: str, fn: Callable[[], _Result], default: _Result, warnings: list[str]) -> _Result:
        """The one graceful-degradation boundary for whole-stage calls
        (see module docstring) — catches any exception `fn` raises,
        substituting a neutral default so the rest of process() is
        unaffected."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- intentional catch-all, see docstring above
            warnings.append(f"{name} stage failed: {exc}")
            return default
