"""Shared (ProcessedDocument, ClassificationResult) fixture factories for
this package's tests. Both are built directly via their own dataclasses
(no PDF parsing, no real classification pipeline run) — this package's
profilers only ever read already-computed fields from both, never
re-derive them, so a unit test of this package's own logic has no reason
to pay Phase 1.1/1.2's cost. See test_pipeline.py for the one
integration test that runs the real Phase 1.1 + Phase 1.2 pipelines end
to end.
"""

from datetime import datetime, timezone
from typing import Optional

import pytest

from backend.classification.pass2.enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from backend.classification.pass2.models import ClassificationDecision, ClassificationResult
from backend.document_understanding.enums import DocumentLanguage, SectionType
from backend.document_understanding.models import (
    DocumentMetadata,
    DocumentQuality,
    DocumentStatistics,
    DocumentStructure,
    ProcessedDocument,
)


def make_decision(label, confidence: float = 0.8) -> ClassificationDecision:
    return ClassificationDecision(
        label=label, confidence=confidence, evidence=[f"evidence for {label}"], reasoning=None
    )


def make_document(
    full_text: str = "x" * 100,
    word_count: int = 2000,
    reference_count: int = 10,
    section_count: int = 4,
    normalized_headings: Optional[dict[SectionType, str]] = None,
    quality_confidence: float = 0.8,
    quality_warnings: Optional[list[str]] = None,
) -> ProcessedDocument:
    structure = DocumentStructure(normalized_headings=normalized_headings or {})
    statistics = DocumentStatistics(word_count=word_count, reference_count=reference_count, section_count=section_count)
    quality = DocumentQuality(confidence=quality_confidence, warnings=quality_warnings or [])
    return ProcessedDocument(
        id="test-doc",
        metadata=DocumentMetadata(language=DocumentLanguage.ENGLISH),
        structure=structure,
        statistics=statistics,
        quality=quality,
        traceability={},
        full_text=full_text,
        schema_version="1.0.0",
        pipeline_version="1.0.0",
        processing_time_ms=0.0,
        created_at=datetime.now(timezone.utc),
    )


def make_classification(
    document_type: DocumentType = DocumentType.RESEARCH_ARTICLE,
    domain: ScientificDomain = ScientificDomain.MEDICINE,
    study_design: StudyDesign = StudyDesign.RCT,
    reporting_guideline: ReportingGuideline = ReportingGuideline.CONSORT,
    document_type_confidence: float = 0.8,
    domain_confidence: float = 0.8,
    study_design_confidence: float = 0.8,
    reporting_guideline_confidence: float = 0.8,
    detected_keywords: Optional[list[str]] = None,
) -> ClassificationResult:
    return ClassificationResult(
        document_type=make_decision(document_type, document_type_confidence),
        domain=make_decision(domain, domain_confidence),
        study_design=make_decision(study_design, study_design_confidence),
        reporting_guideline=make_decision(reporting_guideline, reporting_guideline_confidence),
        detected_keywords=detected_keywords or [],
        candidate_labels={},
        warnings=[],
        processing_time_ms=0.0,
        pipeline_version="1.0.0",
    )


@pytest.fixture
def document_factory():
    return make_document


@pytest.fixture
def classification_factory():
    return make_classification
