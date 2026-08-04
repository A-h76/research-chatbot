"""Unit tests for arXiv scholarly client (#24)."""

from __future__ import annotations

from backend.scholarly.arxiv import (
    ArxivWork,
    _parse_feed,
    normalize_arxiv_id,
    pdf_url_for,
)


SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2107.12345v1</id>
    <title>Attention Is All You Sample</title>
    <summary>We propose a thing.</summary>
    <published>2021-07-26T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
    <arxiv:primary_category term="cs.LG"/>
    <category term="cs.LG"/>
    <arxiv:doi>10.48550/arXiv.2107.12345</arxiv:doi>
  </entry>
</feed>
"""


def test_normalize_arxiv_id():
    assert normalize_arxiv_id("2107.12345") == "2107.12345"
    assert normalize_arxiv_id("arXiv:2107.12345v2") == "2107.12345"
    assert normalize_arxiv_id("https://arxiv.org/abs/2107.12345") == "2107.12345"
    assert normalize_arxiv_id("https://arxiv.org/pdf/2107.12345.pdf") == "2107.12345"
    assert normalize_arxiv_id("hep-th/9901001") == "hep-th/9901001"
    assert normalize_arxiv_id("not-an-id") == ""


def test_pdf_url_for():
    assert pdf_url_for("2107.12345").endswith("/2107.12345.pdf")


def test_parse_feed():
    works = _parse_feed(SAMPLE_ATOM)
    assert len(works) == 1
    w = works[0]
    assert isinstance(w, ArxivWork)
    assert w.arxiv_id == "2107.12345"
    assert "Attention" in w.title
    assert "Ada Lovelace" in w.authors
    assert w.year == 2021
    assert w.doi.startswith("10.")
    assert "cs.LG" in w.concepts
    assert w.is_open_access is True
    assert "2107.12345.pdf" in w.open_access_url


def test_search_id_shortcut(monkeypatch):
    from backend.scholarly import arxiv as mod

    captured = {}

    def fake_get(aid, *, db):
        captured["id"] = aid
        return ArxivWork(id=aid, arxiv_id=aid, title="Direct")

    monkeypatch.setattr(mod, "get_work_by_id", fake_get)
    out = mod.search_works("arXiv:2107.12345", page=1, per_page=5, db=None)
    assert captured["id"] == "2107.12345"
    assert out[0].title == "Direct"


def test_download_pdf_checks_magic(monkeypatch):
    from backend.scholarly import arxiv as mod

    class Resp:
        status_code = 200

        def iter_content(self, chunk_size=65536):
            yield b"%PDF-1.4 fake"

    monkeypatch.setattr(
        mod.requests,
        "get",
        lambda *a, **k: Resp(),
    )
    hit = mod.download_pdf(ArxivWork(id="2107.12345", arxiv_id="2107.12345"))
    assert hit is not None
    data, name = hit
    assert data.startswith(b"%PDF")
    assert "2107.12345" in name
