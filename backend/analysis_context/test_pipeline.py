"""Integration tests for AnalysisContextPipeline.

test_processes_real_phase_1_1_and_1_2_output is the one test in this
package that runs Phase 1.1 and Phase 1.2's real pipelines end to end
(PyMuPDF-generated PDF, no binary fixture) — everything else uses the
lightweight document_factory/classification_factory (see conftest.py),
since this package's own logic never re-parses or re-classifies anything
those two phases already computed.
"""

import fitz
import pytest

from backend.analysis_context.enums import RoutingDecision
from backend.analysis_context.models import AnalysisContext, RoutingProfile
from backend.analysis_context.pipeline import AnalysisContextPipeline
from backend.classification.pass2.enums import ScientificDomain, StudyDesign
from backend.classification.pass2.pipeline import DocumentClassificationPipeline
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline


@pytest.fixture
def pipeline():
    return AnalysisContextPipeline()


def test_processes_real_phase_1_1_and_1_2_output(tmp_path, pipeline):
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "A Randomized Controlled Trial of Something\n\n"
        "Abstract\nWe conducted a randomized controlled trial following the consort statement.\n\n"
        "Methods\nPatients were randomly assigned in this clinical trial at the hospital.\n\n"
        "Results\nStatistically significant improvement was observed.\n\n"
        "Discussion\nThese results confirm the treatment's effect on the disease.\n"
    )
    y = 72
    for line in text.splitlines():
        page.insert_text((72, y), line)
        y += 14
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()

    processed = DocumentUnderstandingPipeline().process(path)
    classification = DocumentClassificationPipeline().process(processed)
    context = pipeline.process(processed, classification)

    assert isinstance(context, AnalysisContext)
    assert context.document_profile.domain == ScientificDomain.MEDICINE
    assert context.document_profile.study_design == StudyDesign.RCT
    assert context.routing_profile.primary_routing == RoutingDecision.CLINICAL_TRIAL
    assert context.pipeline_version
    assert context.processing_time_ms >= 0.0
    assert context.confidence.overall > 0.0


def test_raises_for_wrong_input_types(document_factory, classification_factory, pipeline):
    with pytest.raises(TypeError):
        pipeline.process({"not": "a document"}, classification_factory())
    with pytest.raises(TypeError):
        pipeline.process(document_factory(), {"not": "a classification"})


def test_all_five_profiles_and_quality_and_confidence_are_populated(document_factory, classification_factory, pipeline):
    context = pipeline.process(document_factory(), classification_factory())
    assert context.document_profile is not None
    assert context.section_profile is not None
    assert context.analysis_profile is not None
    assert context.routing_profile is not None
    assert context.prompt_profile is not None
    assert context.quality_profile is not None
    assert context.confidence is not None


def test_a_failing_profiler_degrades_with_a_warning_not_a_crash(document_factory, classification_factory):
    class _BrokenDocumentProfiler:
        def profile(self, document, classification):
            raise RuntimeError("boom")

    pipeline = AnalysisContextPipeline(document_profiler=_BrokenDocumentProfiler())
    context = pipeline.process(document_factory(), classification_factory())

    assert context.document_profile.confidence == 0.0
    assert any("document_profile profiler failed" in w for w in context.warnings)
    # the other profiles still ran normally, unaffected by document_profile's failure
    assert isinstance(context.routing_profile, RoutingProfile)
    assert context.routing_profile.primary_routing == RoutingDecision.CLINICAL_TRIAL


def test_thin_input_produces_a_validation_warning(document_factory, classification_factory, pipeline):
    context = pipeline.process(document_factory(full_text=""), classification_factory())
    assert any("no extractable text" in w for w in context.warnings)
