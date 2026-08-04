"""Unit tests for ORCID scholarly client (#26)."""

from __future__ import annotations

from backend.scholarly.orcid import (
    OrcidWork,
    _flatten_groups,
    _work_from_summary,
    external_item_id_for,
    normalize_orcid_id,
    parse_work_id,
)

SAMPLE_PAYLOAD = {
    "group": [
        {
            "work-summary": [
                {
                    "put-code": 152600,
                    "title": {"title": {"value": "ORCID sample work"}},
                    "journal-title": {"value": "Nature"},
                    "publication-date": {"year": {"value": "2020"}},
                    "external-ids": {
                        "external-id": [
                            {
                                "external-id-type": "doi",
                                "external-id-value": "10.1234/orcid.sample",
                            },
                            {
                                "external-id-type": "pmid",
                                "external-id-value": "321",
                            },
                        ]
                    },
                }
            ]
        }
    ]
}


def test_normalize_orcid_id():
    assert normalize_orcid_id("0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert normalize_orcid_id("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert normalize_orcid_id("0000000218250097") == "0000-0002-1825-0097"
    assert normalize_orcid_id("not-an-orcid") == ""


def test_parse_and_external_id():
    assert external_item_id_for("0000-0002-1825-0097", 152600) == "0000-0002-1825-0097:152600"
    assert parse_work_id("0000-0002-1825-0097:152600") == ("0000-0002-1825-0097", "152600")
    assert parse_work_id("bad") == ("", "")


def test_work_from_summary():
    summary = SAMPLE_PAYLOAD["group"][0]["work-summary"][0]
    w = _work_from_summary(summary, orcid_id="0000-0002-1825-0097")
    assert isinstance(w, OrcidWork)
    assert w.put_code == "152600"
    assert w.doi.startswith("10.")
    assert w.pmid == "321"
    assert w.id == "0000-0002-1825-0097:152600"
    assert w.source == "orcid"


def test_flatten_groups():
    works = _flatten_groups(SAMPLE_PAYLOAD, orcid_id="0000-0002-1825-0097")
    assert len(works) == 1
    assert "ORCID sample" in works[0].title


def test_search_requires_orcid(monkeypatch):
    from backend.scholarly import orcid as mod

    monkeypatch.setattr(mod, "provider_enabled", lambda p: True)
    assert mod.search_works("malaria", page=1, per_page=5, db=None) == []


def test_download_pdf_from_url(monkeypatch):
    from backend.scholarly import orcid as mod

    class Resp:
        status_code = 200
        headers = {"Content-Type": "application/pdf"}

        def iter_content(self, chunk_size=65536):
            yield b"%PDF-1.4 fake"

        def close(self):
            pass

    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: Resp())
    hit = mod.download_open_access_pdf(
        OrcidWork(
            id="0000-0002-1825-0097:1",
            put_code="1",
            open_access_url="https://example.org/x.pdf",
        )
    )
    assert hit is not None
    data, name = hit
    assert data.startswith(b"%PDF")
    assert "orcid" in name
