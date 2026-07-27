"""Shared fixtures for this package's tests.

make_pdf() builds a real PDF via PyMuPDF (short lines per insert_text()
call — long single lines silently truncate past the page width, a real
pitfall discovered while building this package; keep synthetic test
sentences short, matching every prior phase's own test convention)
and processed_document() runs it through the real Phase 1.1 pipeline —
character offsets are load-bearing throughout this package (every
extractor builds EvidenceReference from them), so hand-constructing a
ProcessedDocument/DocumentStructure with guessed offsets is a real
footgun (also discovered while building this package) this package's own
tests deliberately avoid.

classification_factory/context_factory hand-build ClassificationResult/
AnalysisContext instead — extractors only ever read a few label fields
off these two (study_design, domain, routing_profile.primary_routing,
section_profile.section_completeness), none of which carry character-
offset risk, so a lightweight hand-built factory (matching backend.
analysis_context's own conftest.py convention) is both safe and much
faster than running the real Phase 1.2/1.3 pipelines for every test.
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
from backend.analysis_context.models import (
    AnalysisContext,
    AnalysisProfile,
    AnalysisQualityProfile,
)
from backend.analysis_context.models import ConfidenceScore as AnalysisConfidenceScore
from backend.analysis_context.models import (
    DocumentProfile,
    PromptProfile,
    RoutingProfile,
    SectionProfile,
)
from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from backend.classification.pass2.models import ClassificationDecision, ClassificationResult
from backend.document_understanding.enums import QualityLevel, SectionType
from backend.document_understanding.models import ProcessedDocument
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline


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


@pytest.fixture
def pdf_factory(tmp_path):
    return lambda pages: make_pdf(tmp_path, pages)


@pytest.fixture
def classification_factory():
    return make_classification


@pytest.fixture
def context_factory():
    return make_context
