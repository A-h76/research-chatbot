"""Shared fixtures for knowledge_graph tests."""

from pathlib import Path

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
from backend.evidence_grading.models import EvidenceGrades, Grade, OutcomeGrade
from backend.medical_understanding.enums import ClinicalEntityType, EntityNormalizationStatus
from backend.medical_understanding.models import (
    ClinicalEntity,
    ConfidenceScore as MedicalConfidence,
    Intervention,
    MedicalUnderstanding,
    Outcome,
    PICOElements,
    Population,
)
from backend.document_understanding.models import EvidenceReference
from backend.prompt_assembly.models import AssembledPrompt, ConfidenceScore as PromptConfidence


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
    study_design: StudyDesign = StudyDesign.RCT,
    domain: ScientificDomain = ScientificDomain.MEDICINE,
) -> ClassificationResult:
    return ClassificationResult(
        document_type=make_decision(DocumentType.RESEARCH_ARTICLE),
        domain=make_decision(domain),
        study_design=make_decision(study_design),
        reporting_guideline=make_decision(ReportingGuideline.CONSORT),
        detected_keywords=[],
        candidate_labels={},
        warnings=[],
        processing_time_ms=0.0,
        pipeline_version="1.0.0",
    )


def make_context(primary_routing: RoutingDecision = RoutingDecision.CLINICAL_TRIAL) -> AnalysisContext:
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
        section_profile=SectionProfile(section_completeness={SectionType.RESULTS: 0.9}),
        routing_profile=RoutingProfile(
            primary_routing=primary_routing,
            module_pipeline=["medical_understanding", "evidence_grading", "prompt_assembly", "knowledge_graph"],
            fallback_strategy=FallbackStrategy.NONE,
            confidence=0.8,
        ),
        prompt_profile=PromptProfile(
            prompt_family=PromptFamily.CLINICAL,
            prompt_strategy=PromptStrategy.PICO_FIRST,
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


def _ref(snippet: str = "snippet") -> EvidenceReference:
    return EvidenceReference(
        page=1,
        section=None,
        paragraph=None,
        character_range=None,
        text_snippet=snippet,
        confidence=0.9,
    )


def make_medical(skipped: bool = False) -> MedicalUnderstanding:
    if skipped:
        return MedicalUnderstanding(
            skipped=True,
            reasoning="not medical",
            confidence=MedicalConfidence(overall=0.0, components={}, formula=""),
        )
    entities = [
        ClinicalEntity(
            value="Metformin",
            entity_type=ClinicalEntityType.DRUG,
            raw_text="metformin",
            normalization_status=EntityNormalizationStatus.EXACT_MATCH,
            confidence=0.9,
            evidence=_ref("metformin"),
        ),
        ClinicalEntity(
            value="Type 2 Diabetes",
            entity_type=ClinicalEntityType.CONDITION,
            raw_text="type 2 diabetes",
            normalization_status=EntityNormalizationStatus.EXACT_MATCH,
            confidence=0.95,
            evidence=_ref("diabetes"),
        ),
    ]
    pico = PICOElements(
        population=Population(description="Adults with Type 2 Diabetes", confidence=0.8, evidence=_ref()),
        interventions=[Intervention(name="Metformin", confidence=0.9, evidence=_ref())],
        outcomes=[Outcome(name="HbA1c", confidence=0.85, evidence=_ref())],
        confidence=0.8,
    )
    return MedicalUnderstanding(
        skipped=False,
        clinical_entities=entities,
        pico_elements=pico,
        interventions=pico.interventions,
        populations=[pico.population] if pico.population else [],
        outcomes=pico.outcomes,
        confidence=MedicalConfidence(overall=0.8, components={}, formula=""),
    )


def make_grades(skipped: bool = False) -> EvidenceGrades:
    if skipped:
        return EvidenceGrades(skipped=True, reasoning="not required")
    return EvidenceGrades(
        skipped=False,
        overall_grade=Grade(grade_value="moderate", confidence=0.8),
        outcome_grades={
            "HbA1c": OutcomeGrade(
                outcome_name="HbA1c",
                grade=Grade(grade_value="moderate", confidence=0.8),
                confidence=0.8,
                evidence=[_ref()],
            )
        },
        confidence=GradeConfidence(overall=0.75, components={}, formula=""),
    )


def make_prompt() -> AssembledPrompt:
    return AssembledPrompt(
        system_prompt="You are an analyst.",
        user_prompt="Analyze the study.",
        full_prompt="You are an analyst.\n\nAnalyze the study.",
        prompt_family=PromptFamily.CLINICAL,
        prompt_strategy=PromptStrategy.PICO_FIRST,
        confidence_score=PromptConfidence(overall=0.8, components={}, formula=""),
        pipeline_version="1.0.0",
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


@pytest.fixture
def prompt_factory():
    return make_prompt
