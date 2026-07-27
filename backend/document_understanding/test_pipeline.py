"""End-to-end tests for DocumentUnderstandingPipeline — real PDFs (see
conftest.py's make_pdf fixture), asserting the graceful-degradation
requirement directly: .process() must never raise for a document-shaped
problem (corrupt, encrypted, unsupported format, no extractable text).
"""

from pathlib import Path

import fitz
import pytest

from backend.document_understanding.enums import ExtractionStatus, SectionType
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline


@pytest.fixture
def pipeline():
    return DocumentUnderstandingPipeline()


def _stage(result, name):
    return next(log for log in result.stage_logs if log.stage == name)


def test_processes_a_real_paper_end_to_end(make_pdf, pipeline):
    page1 = (
        "A Study of Something Important\nJane Doe, John Smith\n\nJournal of Important Studies\n\n"
        "Abstract\nThis paper studies something important for the field.\n\n"
        "1. Introduction\nBackground and context for the reader in some detail.\n"
    )
    page2 = (
        "2. Methods\nA randomized controlled trial design was used throughout.\n\n"
        "Results\nSignificant effects were found across all conditions.\n\n"
        "Discussion\nThis confirms the hypothesis under study.\n\n"
        "References\n[1] A citation.\n"
    )
    path = make_pdf([page1, page2], metadata={"title": "A Study of Something Important"})

    result = pipeline.process(path)

    assert result.metadata.title == "A Study of Something Important"
    assert SectionType.METHODS in result.structure.normalized_headings
    assert result.statistics.page_count == 2
    assert result.quality.confidence > 0.0
    assert result.traceability
    assert result.schema_version
    assert result.pipeline_version
    assert result.created_at is not None
    assert {log.stage for log in result.stage_logs} == {
        "parser",
        "language",
        "sections",
        "metadata",
        "statistics",
        "quality",
        "traceability",
    }
    assert all(log.status == ExtractionStatus.SUCCESS for log in result.stage_logs)


def test_processing_completes_well_under_five_seconds(make_pdf, pipeline):
    path = make_pdf(["Some content.\n" * 20])
    result = pipeline.process(path)
    assert result.processing_time_ms < 5000


def test_encrypted_pdf_never_raises(make_pdf, pipeline):
    path = make_pdf(["Secret content."], encrypt=True)

    result = pipeline.process(path)

    assert _stage(result, "parser").status == ExtractionStatus.FAILED
    assert "encrypted" in _stage(result, "parser").errors[0]
    assert result.quality is not None


def test_corrupted_pdf_never_raises(tmp_path, pipeline):
    path = Path(tmp_path) / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.4 not a real pdf body at all")

    result = pipeline.process(path)

    assert _stage(result, "parser").status == ExtractionStatus.FAILED
    assert result.metadata is not None
    assert result.quality.level is not None


def test_unsupported_format_never_raises(tmp_path, pipeline):
    path = Path(tmp_path) / "notes.txt"
    path.write_text("hello world")

    result = pipeline.process(path)

    parser_log = _stage(result, "parser")
    assert parser_log.status == ExtractionStatus.PARTIAL
    assert "unsupported" in parser_log.warnings[0]


def test_scanned_like_pdf_with_no_text_never_raises(tmp_path, pipeline):
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    path = Path(tmp_path) / "scanned.pdf"
    doc.save(str(path))
    doc.close()

    result = pipeline.process(path)

    assert result.quality.errors
    assert result.quality.confidence == 0.0


def test_caller_supplied_id_is_honored(make_pdf, pipeline):
    path = make_pdf(["Some content."])
    result = pipeline.process(path, metadata={"id": "my-custom-id"})
    assert result.id == "my-custom-id"


def test_id_is_minted_when_not_supplied(make_pdf, pipeline):
    path = make_pdf(["Some content."])
    result = pipeline.process(path)
    assert result.id


def test_injected_components_are_used_instead_of_defaults(make_pdf):
    calls = []

    class _RecordingLanguageDetector:
        def detect(self, text):
            calls.append(text)
            from backend.document_understanding.enums import DocumentLanguage
            from backend.document_understanding.models import LanguageDetectionResult

            return LanguageDetectionResult(DocumentLanguage.UNKNOWN, 0.0, "stub")

    path = make_pdf(["Some content."])
    pipeline = DocumentUnderstandingPipeline(language_detector=_RecordingLanguageDetector())
    pipeline.process(path)

    assert len(calls) == 1
