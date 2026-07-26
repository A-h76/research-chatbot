"""Shared fixtures for this package's tests.

make_pdf()/process_pdf() mirror backend.medical_understanding's own
conftest.py exactly (short lines per insert_text() call — long single
lines silently truncate past the page width; real synthetic PDFs via
PyMuPDF, no binary fixtures).

classification_factory/context_factory/medical_factory hand-build
ClassificationResult/AnalysisContext/MedicalUnderstanding instead of
running the real Phase 1.2-1.4 pipelines — this package's own
assessors/frameworks only ever read a handful of label/list fields off
these three (study_design, medical.outcomes/statistical_measures/
populations, routing_profile.module_pipeline), none of which carry
character-offset risk, so lightweight hand-built factories are both safe
and much faster than re-running three upstream pipelines per test.

context_factory's module_pipeline matters here in a way it didn't for
backend.medical_understanding's identical-looking fixture: that
package's own _should_run() checks routing_profile.primary_routing
directly, but this package's EvidenceGradingPipeline._should_run()
checks for "evidence_grading" inside routing_profile.module_pipeline
(mirroring the real backend.analysis_context.routing_profile._MODULE_
PIPELINES mapping) — so this factory sets module_pipeline explicitly
rather than leaving it at its empty-list default.
"""

from pathlib import Path
from typing import Optional

import fitz
import pytest

from backend.analysis_context.enums import (
    AudienceType,
    ComplexityLevel,
    FallbackStrategy,
    PromptFamily,
    PromptStrategy,
    RoutingDecision,
)
from backend.analysis_context.models import AnalysisContext, AnalysisProfile, AnalysisQualityProfile
from backend.analysis_context.models import ConfidenceScore as AnalysisConfidenceScore
from backend.analysis_context.models import DocumentProfile, PromptProfile, RoutingProfile, SectionProfile
from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from backend.classification.pass2.models import ClassificationDecision, ClassificationResult
from backend.document_understanding.enums import QualityLevel, SectionType
from backend.document_understanding.models import ProcessedDocument
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline
from backend.medical_understanding.models import ConfidenceScore as MedicalConfidenceScore
from backend.medical_understanding.models import MedicalUnderstanding

_MODULE_PIPELINES_BY_ROUTING = {
    RoutingDecision.CLINICAL_TRIAL: ["medical_understanding", "bias_assessment", "evidence_grading", "prompt_assembly"],
    RoutingDecision.SYSTEMATIC_REVIEW: [
        "medical_understanding",
        "evidence_grading",
        "consensus_detection",
        "prompt_assembly",
    ],
    RoutingDecision.MEDICAL_FULL: ["medical_understanding", "domain_extraction", "prompt_assembly"],
    RoutingDecision.GENERIC: ["generic_understanding", "prompt_assembly"],
    RoutingDecision.UNKNOWN: ["generic_understanding"],
}


def make_pdf(tmp_path: Path, pages: list[str]) -> Path:
    doc = fitz.open()
    for page_text in pages:
        page = doc.new_page()
        y = 72
        for line in page_text.splitlines():
            page.insert_text((72, y), line)
            y += 14
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()
    return path


def process_pdf(path: Path) -> ProcessedDocument:
    return DocumentUnderstandingPipeline().process(path)


def make_decision(label, confidence: float = 0.8) -> ClassificationDecision:
    return ClassificationDecision(label=label, confidence=confidence, evidence=[], reasoning=None)


def make_classification(
    document_type: DocumentType = DocumentType.RESEARCH_ARTICLE,
    domain: ScientificDomain = ScientificDomain.MEDICINE,
    study_design: StudyDesign = StudyDesign.RCT,
    reporting_guideline: ReportingGuideline = ReportingGuideline.CONSORT,
) -> ClassificationResult:
    return ClassificationResult(
        document_type=make_decision(document_type),
        domain=make_decision(domain),
        study_design=make_decision(study_design),
        reporting_guideline=make_decision(reporting_guideline),
        detected_keywords=[],
        candidate_labels={},
        warnings=[],
        processing_time_ms=0.0,
        pipeline_version="1.0.0",
    )


def make_context(
    primary_routing: RoutingDecision = RoutingDecision.CLINICAL_TRIAL,
    section_completeness: Optional[dict[SectionType, float]] = None,
) -> AnalysisContext:
    document_profile = DocumentProfile(
        document_type=DocumentType.RESEARCH_ARTICLE,
        domain=ScientificDomain.MEDICINE,
        study_design=StudyDesign.RCT,
        reporting_guideline=ReportingGuideline.CONSORT,
        intended_audience=AudienceType.CLINICAL,
        complexity_level=ComplexityLevel.MODERATE,
        confidence=0.8,
    )
    section_profile = SectionProfile(section_completeness=section_completeness or {SectionType.METHODS: 1.0})
    analysis_profile = AnalysisProfile(confidence=0.8)
    routing_profile = RoutingProfile(
        primary_routing=primary_routing,
        module_pipeline=_MODULE_PIPELINES_BY_ROUTING.get(primary_routing, _MODULE_PIPELINES_BY_ROUTING[RoutingDecision.GENERIC]),
        fallback_strategy=FallbackStrategy.NONE,
        confidence=0.8,
    )
    prompt_profile = PromptProfile(
        prompt_family=PromptFamily.CLINICAL,
        prompt_strategy=PromptStrategy.SECTION_BASED,
        confidence=0.8,
    )
    quality_profile = AnalysisQualityProfile(
        input_document_quality=0.8,
        input_classification_confidence=0.8,
        reliability_score=0.8,
        reliability_level=QualityLevel.GOOD,
    )
    return AnalysisContext(
        document_profile=document_profile,
        analysis_profile=analysis_profile,
        section_profile=section_profile,
        routing_profile=routing_profile,
        prompt_profile=prompt_profile,
        quality_profile=quality_profile,
        confidence=AnalysisConfidenceScore(
            overall=0.8,
            document_profile=0.8,
            section_profile=0.8,
            analysis_profile=0.8,
            routing_profile=0.8,
            prompt_profile=0.8,
        ),
        warnings=[],
        processing_time_ms=0.0,
        pipeline_version="1.0.0",
    )


def make_medical(skipped: bool = False, confidence_overall: float = 0.7, **overrides) -> MedicalUnderstanding:
    confidence = MedicalConfidenceScore(overall=confidence_overall, components={}, formula="")
    return MedicalUnderstanding(skipped=skipped, confidence=confidence, **overrides)


@pytest.fixture
def pdf_factory(tmp_path):
    return lambda pages: make_pdf(tmp_path, pages)


@pytest.fixture
def classification_factory():
    return make_classification


@pytest.fixture
def context_factory():
    return make_context


@pytest.fixture
def medical_factory():
    return make_medical
