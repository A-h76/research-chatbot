"""Unit tests for PubMed scholarly client (#22)."""

from __future__ import annotations

from backend.scholarly.pubmed import (
    PubmedWork,
    _parse_esummary_item,
    normalize_pmcid,
    normalize_pmid,
)


def test_normalize_pmid():
    assert normalize_pmid("12345") == "12345"
    assert normalize_pmid("PMID: 12345") == "12345"
    assert normalize_pmid("pmid 00099") == "99"
    assert normalize_pmid("not-a-pmid") == ""
    assert normalize_pmid("") == ""


def test_normalize_pmcid():
    assert normalize_pmcid("PMC123") == "PMC123"
    assert normalize_pmcid("123") == "PMC123"
    assert normalize_pmcid("") == ""


def test_parse_esummary_item_extracts_ids():
    item = {
        "uid": "31452104",
        "title": "Example title.",
        "source": "Nature",
        "fulljournalname": "Nature",
        "pubdate": "2019 Sep",
        "authors": [{"name": "Doe J"}, {"name": "Smith A"}],
        "articleids": [
            {"idtype": "pubmed", "value": "31452104"},
            {"idtype": "doi", "value": "10.1038/s41586-019-1490-y"},
            {"idtype": "pmc", "value": "PMC6789012"},
        ],
    }
    work = _parse_esummary_item("31452104", item)
    assert isinstance(work, PubmedWork)
    assert work.pmid == "31452104"
    assert work.doi == "10.1038/s41586-019-1490-y"
    assert work.pmcid == "PMC6789012"
    assert work.year == 2019
    assert "Doe J" in work.authors
    assert "pmc/articles/PMC6789012/pdf" in work.open_access_url
    assert work.source == "pubmed"


def test_search_works_pmid_shortcut(monkeypatch):
    from backend.scholarly import pubmed as mod

    captured = {}

    def fake_get(pmid, *, db, enrich=True):
        captured["pmid"] = pmid
        return PubmedWork(id=pmid, pmid=pmid, title="Direct")

    monkeypatch.setattr(mod, "get_work_by_pmid", fake_get)
    out = mod.search_works("PMID: 42", page=1, per_page=5, db=None, enrich=False)
    assert captured["pmid"] == "42"
    assert len(out) == 1
    assert out[0].title == "Direct"


def test_search_works_uses_esearch(monkeypatch):
    from backend.scholarly import pubmed as mod

    class FakeCache:
        def __init__(self, db, provider):
            pass

    def fake_get_or_fetch(cache, key, fetch_fn, **kwargs):
        return {"esearchresult": {"idlist": ["111", "222"]}}

    def fake_esummary(pmids, *, db):
        return [
            PubmedWork(id=p, pmid=p, title=f"T{p}") for p in pmids
        ]

    monkeypatch.setattr(mod, "ProviderCache", FakeCache)
    monkeypatch.setattr(mod, "get_or_fetch", fake_get_or_fetch)
    monkeypatch.setattr(mod, "_esummary_works", fake_esummary)
    monkeypatch.setattr(mod, "_enrich_from_europepmc", lambda w, *, db: w)

    out = mod.search_works("crp inflammation", page=1, per_page=10, db=object(), enrich=True)
    assert [w.pmid for w in out] == ["111", "222"]
