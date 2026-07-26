"""Shared fixtures for prompt_assembly tests."""

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
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline
from backend.evidence_grading.models import ConfidenceScore as GradeConfidence
from backend.evidence_grading.models import EvidenceGrades, Grade
from backend.medical_understanding.models import ConfidenceScore as MedicalConfidence
from backend.medical_understanding.models import MedicalUnderstanding, Outcome, PICOElements, Population


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


def process_pdf(path: Path):
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


_MODULE_PIPELINES = {
    RoutingDecision.CLINICAL_TRIAL: ["medical_understanding", "evidence_grading", "prompt_assembly"],
    RoutingDecision.SYSTEMATIC_REVIEW: ["medical_understanding", "evidence_grading", "prompt_assembly"],
    RoutingDecision.MEDICAL_FULL: ["medical_understanding", "prompt_assembly"],
    RoutingDecision.GENERIC: ["generic_understanding", "prompt_assembly"],
}


def make_context(
    primary_routing: RoutingDecision = RoutingDecision.CLINICAL_TRIAL,
    prompt_family: PromptFamily = PromptFamily.CLINICAL,
    prompt_strategy: PromptStrategy = PromptStrategy.PICO_FIRST,
) -> AnalysisContext:
    return AnalysisContext(
        document_profile=DocumentProfile(
            document_type=DocumentType.RESEARCH_ARTICLE,
            domain=ScientificDomain.MEDICINE,
            study_design=StudyDesign.RCT,
            reporting_guideline=ReportingGuideline.CONSORT,
            intended_audience=AudienceType.CLINICAL,
            complexity_level=ComplexityLevel.MODERATE,
            confidence=0.8,
        ),
        analysis_profile=AnalysisProfile(confidence=0.8),
        section_profile=SectionProfile(section_completeness={SectionType.RESULTS: 0.9, SectionType.METHODS: 1.0}),
        routing_profile=RoutingProfile(
            primary_routing=primary_routing,
            module_pipeline=_MODULE_PIPELINES.get(primary_routing, ["prompt_assembly"]),
            fallback_strategy=FallbackStrategy.NONE,
            confidence=0.8,
        ),
        prompt_profile=PromptProfile(
            prompt_family=prompt_family,
            prompt_strategy=prompt_strategy,
            section_priorities=[SectionType.METHODS, SectionType.RESULTS, SectionType.ABSTRACT],
            confidence=0.8,
        ),
        quality_profile=AnalysisQualityProfile(
            input_document_quality=0.8,
            input_classification_confidence=0.8,
            reliability_score=0.8,
            reliability_level=QualityLevel.GOOD,
        ),
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


def make_medical(skipped: bool = False, with_pico: bool = True) -> MedicalUnderstanding:
    pico = None
    if with_pico and not skipped:
        pico = PICOElements(
            population=Population(description="Adults with type 2 diabetes", confidence=0.8),
            interventions=[],
            comparators=[],
            outcomes=[Outcome(name="HbA1c", confidence=0.8)],
            confidence=0.7,
        )
        # interventions needed for pico_is_complete — add one
        from backend.medical_understanding.models import Intervention

        pico.interventions = [Intervention(name="metformin", confidence=0.8)]
    return MedicalUnderstanding(
        skipped=skipped,
        reasoning="not medical" if skipped else None,
        confidence=MedicalConfidence(overall=0.7 if not skipped else 0.0, components={}, formula=""),
        pico_elements=pico,
        outcomes=pico.outcomes if pico else [],
    )


def make_grades(skipped: bool = False) -> EvidenceGrades:
    if skipped:
        return EvidenceGrades(skipped=True, reasoning="not required")
    return EvidenceGrades(
        skipped=False,
        overall_grade=Grade(grade_value="moderate", confidence=0.8),
        confidence=GradeConfidence(overall=0.75, components={}, formula=""),
    )


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


@pytest.fixture
def grades_factory():
    return make_grades
