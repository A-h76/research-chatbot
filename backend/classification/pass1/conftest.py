"""Shared test fixtures for backend/classification/pass1's test suite.

make_document builds a ProcessedDocument (backend.processing.models) by
hand with sensible defaults, since every Pass 1 classifier's real input
contract is ProcessedDocument, not a PDF file — backend/processing's own
test suite already covers turning a PDF into one of these correctly.
"""

from datetime import datetime, timezone

import pytest

from backend.processing.models import DocumentQuality, ProcessedDocument

_HAS_FLAGS = ("has_abstract", "has_methods", "has_results", "has_discussion", "has_references")


def _quality(**has_flags: bool) -> DocumentQuality:
    for name in has_flags:
        assert name in _HAS_FLAGS, f"not a real DocumentQuality has_* flag: {name!r}"
    return DocumentQuality(
        ocr_quality=1.0,
        text_extraction_quality=1.0,
        missing_sections=[],
        has_abstract=has_flags.get("has_abstract", False),
        has_methods=has_flags.get("has_methods", False),
        has_results=has_flags.get("has_results", False),
        has_discussion=has_flags.get("has_discussion", False),
        has_references=has_flags.get("has_references", False),
        confidence=1.0,
        warnings=[],
        errors=[],
    )


@pytest.fixture
def make_document():
    """Factory fixture: make_document(title=..., abstract=..., full_text=...,
    venue=..., has_methods=True, ...) -> ProcessedDocument."""

    def _make(
        title: str = "",
        abstract: str = "",
        full_text: str = "",
        venue: str = "",
        **has_flags: bool,
    ) -> ProcessedDocument:
        return ProcessedDocument(
            id="1",
            title=title,
            authors=[],
            venue=venue,
            year=None,
            doi=None,
            journal=None,
            language="en",
            abstract=abstract,
            keywords=[],
            references=[],
            tables=[],
            figures=[],
            section_order=[],
            raw_sections={},
            normalized_sections={},
            full_text=full_text,
            page_count=1,
            word_count=len(full_text.split()),
            char_count=len(full_text),
            quality=_quality(**has_flags),
            created_at=datetime.now(timezone.utc),
        )

    return _make
