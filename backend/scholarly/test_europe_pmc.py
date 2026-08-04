"""Unit tests for Europe PMC scholarly client (#25)."""

from __future__ import annotations

from backend.scholarly.europe_pmc import (
    EuropePmcWork,
    _work_from_hit,
    normalize_europe_pmc_id,
    normalize_pmcid,
    normalize_pmid,
)


SAMPLE_HIT = {
    "id": "2107",
    "source": "MED",
    "pmid": "2107",
    "pmcid": "PMC7654321",
    "doi": "10.1234/epmc.sample",
    "title": "Europe PMC sample paper",
    "authorString": "Ada Lovelace, Alan Turing",
    "journalTitle": "Nature Methods",
    "pubYear": "2021",
    "abstractText": "We propose a thing.",
    "isOpenAccess": "Y",
    "citedByCount": 12,
    "fullTextUrlList": {
        "fullTextUrl": [
            {
                "availabilityCode": "OA",
                "documentStyle": "pdf",
                "url": "https://example.org/paper.pdf",
            }
        ]
    },
    "meshHeadingList": {"meshHeading": [{"descriptorName": "Machine Learning"}]},
}


def test_normalize_ids():
    assert normalize_pmid("PMID: 2107") == "2107"
    assert normalize_pmcid("7654321") == "PMC7654321"
    assert normalize_pmcid("PMC7654321") == "PMC7654321"
    assert normalize_europe_pmc_id("PMC7654321") == "PMC7654321"
    assert normalize_europe_pmc_id("https://europepmc.org/article/MED/2107") == "2107"
    assert normalize_europe_pmc_id("https://europepmc.org/article/PMC/7654321") == "PMC7654321"
    assert normalize_europe_pmc_id("not-an-id") == ""


def test_work_from_hit():
    w = _work_from_hit(SAMPLE_HIT)
    assert isinstance(w, EuropePmcWork)
    assert w.pmcid == "PMC7654321"
    assert w.pmid == "2107"
    assert w.id == "PMC7654321"
    assert "Europe PMC" in w.title
    assert w.is_open_access is True
    assert w.open_access_url.endswith(".pdf")
    assert "Machine Learning" in w.concepts
    assert w.source == "europe_pmc"


def test_search_id_shortcut(monkeypatch):
    from backend.scholarly import europe_pmc as mod

    captured = {}

    def fake_get(aid, *, db):
        captured["id"] = aid
        return EuropePmcWork(id="PMC1", pmcid="PMC1", title="Direct")

    monkeypatch.setattr(mod, "get_work_by_id", fake_get)
    out = mod.search_works("PMC7654321", page=1, per_page=5, db=None)
    assert captured["id"] == "PMC7654321"
    assert out[0].title == "Direct"


def test_download_pdf_checks_magic(monkeypatch):
    from backend.scholarly import europe_pmc as mod

    class Resp:
        status_code = 200
        headers = {"Content-Type": "application/pdf"}

        def iter_content(self, chunk_size=65536):
            yield b"%PDF-1.4 fake"

        def close(self):
            pass

    class Sess:
        def get(self, *a, **k):
            return Resp()

    monkeypatch.setattr(mod.requests, "Session", lambda: Sess())
    hit = mod.download_open_access_pdf(
        EuropePmcWork(
            id="PMC7654321",
            pmcid="PMC7654321",
            open_access_url="https://example.org/x.pdf",
        )
    )
    assert hit is not None
    data, name = hit
    assert data.startswith(b"%PDF")
    assert "PMC7654321" in name
