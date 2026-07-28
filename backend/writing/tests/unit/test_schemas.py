import pytest

from backend.writing.api.errors import WritingDomainError
from backend.writing.validation.schemas import MAX_CONTENT, MAX_TITLE, normalize_document_mutation


def test_normalize_document_mutation_passes():
    doc = normalize_document_mutation("  Title  ", "Body")
    assert doc.title == "Title"
    assert doc.content == "Body"


def test_title_limit_enforced():
    with pytest.raises(WritingDomainError):
        normalize_document_mutation("x" * (MAX_TITLE + 1), "ok")


def test_content_limit_enforced():
    with pytest.raises(WritingDomainError):
        normalize_document_mutation("ok", "x" * (MAX_CONTENT + 1))

