"""Integration tests for MedicalUnderstandingPipeline.

test_processes_a_real_clinical_trial_end_to_end is the one test in this
package that runs Phase 1.1 + Phase 1.2 + Phase 1.3's real pipelines
(PyMuPDF-generated PDF, no binary fixture) — everything else uses the
lightweight classification_factory/context_factory (see conftest.py),
since this package's own logic never re-parses, re-classifies, or
re-profiles anything those three phases already computed.
"""

import pytest

from backend.analysis_context.enums import RoutingDecision
from backend.medical_understanding.conftest import process_pdf
from backend.medical_understanding.interfaces import BaseExtractor
from backend.medical_understanding.models import MedicalUnderstanding
from backend.medical_understanding.pipeline import MedicalUnderstandingPipeline


@pytest.fixture
def pipeline():
    return MedicalUnderstandingPipeline()


_CLINICAL_TEXT = (
    "A Double-Blind Randomized Clinical Trial\n\n"
    "Abstract\n"
    "We conducted a randomized controlled trial in a hospital clinical setting.\n"
    "Patients with diabetes and hypertension were enrolled for treatment and therapy.\n"
    "Physician diagnosis confirmed disease status. Design comparing metformin versus placebo.\n"
    "Primary outcome at 12 weeks.\n\n"
    "Methods\n"
    "Patients were randomly assigned to receive metformin or placebo for clinical treatment.\n"
    "This was a double-blind, multicenter trial with a 2-arm design.\n"
    "Study duration of 24 weeks.\n"
    "Follow-up period of 52 weeks.\n"
    "The trial was conducted across 5 sites.\n\n"
    "Results\n"
    "There was a significant reduction in HbA1c (p=0.002).\n"
    "Patients treated with metformin showed reduced fatigue.\n"
    "Mean difference was 1.2 percentage points.\n\n"
    "Discussion\n"
    "These clinical results confirm the treatment effect on the disease and patient therapy outcomes.\n"
)


def test_processes_a_real_clinical_trial_end_to_end(pdf_factory, pipeline):
    from backend.analysis_context.pipeline import AnalysisContextPipeline
    from backend.classification.pass2.pipeline import DocumentClassificationPipeline

    document = process_pdf(pdf_factory([_CLINICAL_TEXT]))
    classification = DocumentClassificationPipeline().process(document)
    context = AnalysisContextPipeline().process(document, classification)

    understanding = pipeline.process(document, classification, context)

    assert isinstance(understanding, MedicalUnderstanding)
    assert understanding.skipped is False
    assert understanding.clinical_entities
    assert understanding.interventions
    assert understanding.pico_elements is not None
    assert understanding.confidence.overall > 0.0
    assert understanding.extraction_summary.total_entities > 0
    assert understanding.pipeline_version
    assert understanding.processing_time_ms >= 0.0


def test_skips_non_medical_documents(pdf_factory, classification_factory, context_factory, pipeline):
    document = process_pdf(pdf_factory(["A generic non-medical document.\n"]))
    classification = classification_factory()
    context = context_factory(primary_routing=RoutingDecision.GENERIC)

    understanding = pipeline.process(document, classification, context)

    assert understanding.skipped is True
    assert understanding.reasoning is not None
    assert understanding.clinical_entities == []
    assert understanding.errors == []


def test_runs_for_every_medical_routing_decision(pdf_factory, classification_factory, context_factory, pipeline):
    document = process_pdf(pdf_factory(["Abstract\nPatients with diabetes were treated with metformin.\n"]))
    for routing in (
        RoutingDecision.MEDICAL_FULL,
        RoutingDecision.MEDICAL_SCOPED,
        RoutingDecision.CLINICAL_TRIAL,
        RoutingDecision.SYSTEMATIC_REVIEW,
    ):
        context = context_factory(primary_routing=routing)
        understanding = pipeline.process(document, classification_factory(), context)
        assert understanding.skipped is False


def test_raises_for_wrong_input_types(classification_factory, context_factory, pdf_factory, pipeline):
    document = process_pdf(pdf_factory(["Some content."]))
    with pytest.raises(TypeError):
        pipeline.process({"not": "a document"}, classification_factory(), context_factory())
    with pytest.raises(TypeError):
        pipeline.process(document, {"not": "a classification"}, context_factory())
    with pytest.raises(TypeError):
        pipeline.process(document, classification_factory(), {"not": "a context"})


def test_a_failing_extractor_degrades_gracefully(pdf_factory, classification_factory, context_factory):
    class _BrokenExtractor(BaseExtractor):
        def extract(self, index, classification, context, registry):
            raise RuntimeError("boom")

        def supports(self, context):
            return True

        def priority(self):
            return 100

        def version(self):
            return "1.0.0"

        def capabilities(self):
            return ["broken"]

    pipeline = MedicalUnderstandingPipeline()
    pipeline.registry.unregister("clinical_entities")
    pipeline.registry.register("clinical_entities", _BrokenExtractor())

    document = process_pdf(pdf_factory(["Abstract\nPatients with diabetes were treated with metformin.\n"]))
    understanding = pipeline.process(document, classification_factory(), context_factory())

    assert understanding.skipped is False
    assert understanding.errors
    assert understanding.errors[0].extractor == "clinical_entities"
    assert "clinical_entities" in understanding.extraction_summary.failed_extractors
    assert understanding.extraction_summary.partial_success is True


def test_processing_is_deterministic_across_runs(pdf_factory, classification_factory, context_factory, pipeline):
    document = process_pdf(pdf_factory([_CLINICAL_TEXT]))
    classification = classification_factory()
    context = context_factory()

    first = pipeline.process(document, classification, context)
    second = MedicalUnderstandingPipeline().process(document, classification, context)

    first_values = sorted(e.value for e in first.clinical_entities)
    second_values = sorted(e.value for e in second.clinical_entities)
    assert first_values == second_values
    assert len(first.interventions) == len(second.interventions)


def test_extraction_summary_reflects_enabled_and_executed_extractors(
    pdf_factory, classification_factory, context_factory, pipeline
):
    document = process_pdf(pdf_factory(["Abstract\nPatients with diabetes were treated with metformin.\n"]))
    understanding = pipeline.process(document, classification_factory(), context_factory())

    summary = understanding.extraction_summary
    assert set(summary.executed_extractors) == set(summary.enabled_extractors)
    assert summary.overall_success_rate == 1.0
    assert summary.failed_extractors == []


def test_no_entity_state_leaks_between_process_calls_on_the_same_pipeline(
    pdf_factory, classification_factory, context_factory, pipeline
):
    diabetic_document = process_pdf(pdf_factory(["Abstract\nPatients with diabetes were treated.\n"]))
    hypertension_document = process_pdf(pdf_factory(["Abstract\nPatients with hypertension were treated.\n"]))

    first = pipeline.process(diabetic_document, classification_factory(), context_factory())
    second = pipeline.process(hypertension_document, classification_factory(), context_factory())

    assert "diabetes mellitus" in [e.value for e in first.clinical_entities]
    assert "diabetes mellitus" not in [e.value for e in second.clinical_entities]
    assert "hypertension" in [e.value for e in second.clinical_entities]
