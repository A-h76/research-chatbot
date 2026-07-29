"""Phase 1a — ImportAdapter + Mendeley normalize tests."""

from __future__ import annotations

import pytest

from backend.library.adapters import get_adapter
from backend.library.adapters.base import ImportAdapter
from backend.library.mendeley import _parse_document


SAMPLE_BIB = r"""
@article{smith2020,
  author = {Smith, Jane},
  title = {Adapter Test},
  year = {2020},
  doi = {10.1234/adapter.2020},
}
"""


def test_get_adapter_bibtex_and_ris():
    bib = get_adapter("bibtex")
    ris = get_adapter("ris")
    assert bib.name == "bibtex"
    assert ris.name == "ris"
    assert bib.capabilities().file_parse is True
    records = bib.fetch_records(text=SAMPLE_BIB)
    assert len(records) == 1
    assert records[0].doi == "10.1234/adapter.2020"


def test_get_adapter_aliases():
    assert get_adapter("biblatex").name == "bibtex"
    with pytest.raises(KeyError):
        get_adapter("endnote")


def test_openalex_adapter():
    adapter = get_adapter("openalex")
    records = adapter.fetch_records(
        work={
            "id": "https://openalex.org/W1",
            "title": "Discover Paper",
            "doi": "10.1/x",
            "authors": "Ada",
            "year": 2024,
            "venue": "Nature",
            "abstract": "abs",
            "open_access_url": "https://oa.example/p",
        }
    )
    assert len(records) == 1
    assert records[0].source == "openalex"
    assert records[0].title == "Discover Paper"
    assert "from-discover" in records[0].tags


def test_phase1b_hooks_raise_on_file_adapters():
    adapter = get_adapter("bibtex")
    with pytest.raises(NotImplementedError, match="Phase 1b"):
        adapter.synchronize()
    with pytest.raises(NotImplementedError, match="Phase 1b"):
        adapter.import_files()


def test_zotero_mendeley_support_incremental_sync():
    assert get_adapter("zotero").capabilities().incremental_sync is True
    assert get_adapter("mendeley").capabilities().incremental_sync is True


def test_mendeley_parse_document():
    rec = _parse_document(
        {
            "id": "doc-1",
            "title": "Mendeley Paper",
            "authors": [{"first_name": "Jane", "last_name": "Smith"}],
            "year": 2021,
            "source": "Lancet",
            "identifiers": {"doi": "https://doi.org/10.9999/mendeley"},
            "abstract": "Hello",
            "websites": ["https://example.com/paper"],
            "tags": ["security"],
            "type": "journal",
        },
        folder_id="folder-a",
        folder_name="Reading List",
    )
    assert rec is not None
    assert rec.source == "mendeley"
    assert rec.doi == "10.9999/mendeley"
    assert "Smith, Jane" in rec.authors
    assert rec.collection_keys == ["folder-a"]
    assert rec.collection_name == "Reading List"
    assert "from-mendeley" in rec.tags


def test_mendeley_adapter_configured_without_env(monkeypatch):
    for name in (
        "MENDELEY_CLIENT_ID",
        "MENDELEY_CLIENT_SECRET",
        "MENDELEY_APP_ID",
        "MENDELEY_APP_SECRET",
        "MENDELEY_ID",
        "MENDELEY_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    adapter = get_adapter("mendeley")
    assert isinstance(adapter, ImportAdapter)
    assert adapter.configured() is False
    assert adapter.capabilities().oauth is True


def test_zotero_adapter_configured_without_env(monkeypatch):
    for name in (
        "ZOTERO_CLIENT_KEY",
        "ZOTERO_CLIENT_SECRET",
        "ZOTERO_CLIENT_ID",
        "ZOTERO_API_KEY",
        "ZOTERO_API_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    adapter = get_adapter("zotero")
    assert adapter.configured() is False


def test_zotero_configured_accepts_client_id_alias(monkeypatch):
    monkeypatch.delenv("ZOTERO_CLIENT_KEY", raising=False)
    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    monkeypatch.setenv("ZOTERO_CLIENT_ID", "alias-key")
    monkeypatch.setenv("ZOTERO_CLIENT_SECRET", "alias-secret")
    from backend.library import zotero as zotero_mod

    assert zotero_mod.zotero_configured() is True
    assert zotero_mod.zotero_missing_env() == []


def test_mendeley_configured_strips_quotes(monkeypatch):
    monkeypatch.setenv("MENDELEY_CLIENT_ID", '"abcde"')
    monkeypatch.setenv("MENDELEY_CLIENT_SECRET", "'secret-value-16'")
    from backend.library import mendeley as mendeley_mod

    assert mendeley_mod.mendeley_configured() is True
    assert mendeley_mod._client_creds()[0] == "abcde"
