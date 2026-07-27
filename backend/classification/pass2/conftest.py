"""Shared ProcessedDocument fixture factory for pass2's tests.

Builds a backend.document_understanding.ProcessedDocument directly via
its own dataclasses rather than running the full Phase 1.1 pipeline (PDF
parsing, heading detection, ...) — pass2's detectors only ever read
already-computed ProcessedDocument fields, never re-parse, so a unit
test of pass2's own logic has no reason to pay Phase 1.1's cost. See
test_pipeline.py for the one integration test that does exercise a real
Phase 1.1 pipeline end to end.
"""

from datetime import datetime, timezone
from typing import Optional

import pytest

from backend.document_understanding.enums import DocumentLanguage, SectionType
from backend.document_understanding.models import (
    DocumentMetadata,
    DocumentQuality,
    DocumentStatistics,
    DocumentStructure,
    ProcessedDocument,
)


def make_document(
    title: str = "",
    abstract: str = "",
    full_text: str = "",
    venue: str = "",
    journal: Optional[str] = None,
    conference: Optional[str] = None,
    normalized_headings: Optional[dict[SectionType, str]] = None,
) -> ProcessedDocument:
    metadata = DocumentMetadata(
        title=title,
        abstract=abstract,
        venue=venue,
        journal=journal,
        conference=conference,
        language=DocumentLanguage.ENGLISH,
    )
    structure = DocumentStructure(normalized_headings=normalized_headings or {})
    return ProcessedDocument(
        id="test-doc",
        metadata=metadata,
        structure=structure,
        statistics=DocumentStatistics(),
        quality=DocumentQuality(),
        traceability={},
        full_text=full_text,
        schema_version="1.0.0",
        pipeline_version="1.0.0",
        processing_time_ms=0.0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def document_factory():
    return make_document
