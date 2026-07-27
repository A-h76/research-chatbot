"""Integration tests for EvidenceGradingPipeline."""

from backend.analysis_context.enums import RoutingDecision
from backend.classification.pass2.enums import StudyDesign
from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.enums import GradingFramework, RecommendationStrength
from backend.evidence_grading.pipeline import EvidenceGradingPipeline, PIPELINE_VERSION
from backend.medical_understanding.models import Outcome


def test_skips_when_routing_omits_evidence_grading(pdf_factory, classification_factory, context_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["A non-clinical methods paper.\n"]))
    pipeline = EvidenceGradingPipeline()
    result = pipeline.process(
        document,
        classification_factory(),
        context_factory(primary_routing=RoutingDecision.GENERIC),
        medical_factory(),
    )

    assert result.skipped is True
    assert result.reasoning is not None
    assert "evidence_grading" in result.reasoning
    assert result.pipeline_version == PIPELINE_VERSION
    assert result.processing_time_ms >= 0.0


def test_processes_clinical_trial_end_to_end(pdf_factory, classification_factory, context_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    text = (
        "Randomized Controlled Trial\n\n"
        "Methods\n"
        "Patients were randomly assigned to metformin or placebo.\n"
        "This was a double-blind multicenter trial.\n"
        "Intention-to-treat analysis was used.\n"
        "The trial was registered at clinicaltrials.gov.\n\n"
        "Results\n"
        "Hazard ratio 0.72 (95% CI 0.55-0.94).\n"
    )
    document = process_pdf(pdf_factory([text]))
    classification = classification_factory(study_design=StudyDesign.RCT)
    context = context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL)
    medical = medical_factory(
        outcomes=[Outcome(name="mortality", confidence=0.8)],
    )

    result = EvidenceGradingPipeline().process(document, classification, context, medical)

    assert result.skipped is False
    assert result.overall_grade.grade_value
    assert GradingFramework.GRADE in result.framework_results
    assert GradingFramework.OXFORD in result.framework_results
    assert result.confidence.overall >= 0.0
    assert result.audit_trail.decisions
    assert "mortality" in result.outcome_grades
    assert result.pipeline_version == PIPELINE_VERSION


def test_grade_sets_recommendation_strength(pdf_factory, classification_factory, context_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(
        pdf_factory(
            [
                "RCT with random assignment, double-blind, intention-to-treat, "
                "registered at clinicaltrials.gov.\n"
            ]
        )
    )
    result = EvidenceGradingPipeline().process(
        document,
        classification_factory(study_design=StudyDesign.RCT),
        context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL),
        medical_factory(),
    )

    grade_result = result.framework_results[GradingFramework.GRADE].grade_result
    assert grade_result is not None
    assert grade_result.recommendation_strength in (
        RecommendationStrength.STRONG,
        RecommendationStrength.WEAK,
    )


def test_respects_disabled_assessors(pdf_factory, classification_factory, context_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    config = EvidenceGradingConfig(enable_risk_of_bias=False, enable_precision=False)
    document = process_pdf(pdf_factory(["RCT methods section.\n"]))
    pipeline = EvidenceGradingPipeline(config)
    plan = pipeline.registry.get_assessment_plan(context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL))

    assert "risk_of_bias" not in plan.enabled_assessors
    assert "precision" not in plan.enabled_assessors
    assert "directness" in plan.enabled_assessors

    result = pipeline.process(
        document,
        classification_factory(study_design=StudyDesign.RCT),
        context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL),
        medical_factory(),
    )
    assert result.skipped is False


def test_determinism_same_inputs_same_grade(pdf_factory, classification_factory, context_factory, medical_factory):
    from backend.evidence_grading.conftest import process_pdf

    document = process_pdf(pdf_factory(["Randomized double-blind intention-to-treat trial.\n"]))
    classification = classification_factory(study_design=StudyDesign.RCT)
    context = context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL)
    medical = medical_factory()
    pipeline = EvidenceGradingPipeline(EvidenceGradingConfig(enable_parallel=False))

    first = pipeline.process(document, classification, context, medical)
    second = pipeline.process(document, classification, context, medical)

    assert first.overall_grade.grade_value == second.overall_grade.grade_value
    assert first.framework_results[GradingFramework.GRADE].grade.grade_value == (
        second.framework_results[GradingFramework.GRADE].grade.grade_value
    )
