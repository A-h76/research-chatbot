import pytest

from backend.classification.pass2.validators import require_processed_document, validate_document


def test_require_processed_document_raises_on_wrong_type():
    with pytest.raises(TypeError, match="ProcessedDocument"):
        require_processed_document({"not": "a document"})


def test_require_processed_document_accepts_real_document(document_factory):
    require_processed_document(document_factory(full_text="enough text to not matter here"))


def test_validate_document_warns_on_sparse_text(document_factory):
    warnings = validate_document(document_factory(full_text="short"))
    assert any("little extractable text" in w for w in warnings)


def test_validate_document_warns_on_missing_title_and_abstract(document_factory):
    document = document_factory(full_text="x" * 100, title="", abstract="")
    warnings = validate_document(document)
    assert any("no title and no abstract" in w for w in warnings)


def test_validate_document_no_warnings_for_healthy_document(document_factory):
    document = document_factory(title="A Real Title", abstract="A real abstract.", full_text="x" * 100)
    assert validate_document(document) == []
