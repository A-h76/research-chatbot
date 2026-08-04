"""UFTR unit tests — outcomes, validator, cache TTL, retry policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.scholarly.uftr.cache import ttl_for_outcome
from backend.scholarly.uftr.outcomes import FullTextOutcome, content_kind_for_bytes
from backend.scholarly.uftr.resolvers import collect_candidates, normalize_doi
from backend.scholarly.uftr.state import (
    apply_resolution_to_file,
    should_auto_retry,
)
from backend.scholarly.uftr.validator import classify_body
from backend.scholarly.uftr.outcomes import ResolutionAttempt, ResolutionResult


def test_content_kind_pdf():
    assert content_kind_for_bytes(b"%PDF-1.4 hello") == "pdf"


def test_classify_bot_html():
    html = b"<!DOCTYPE html><html>Just a moment... cf-browser-verification challenge-platform</html>"
    assert classify_body(html, "text/html") == FullTextOutcome.BOT_PROTECTION


def test_classify_paywall_html():
    html = b"<html><body>Purchase this article to continue. Institutional access required.</body></html>"
    assert classify_body(html, "text/html") == FullTextOutcome.PUBLISHER_PAYWALL


def test_classify_pdf_ok():
    assert classify_body(b"%PDF-1.7 binary", "application/pdf") is None


def test_ttl_classes():
    assert ttl_for_outcome(FullTextOutcome.FOUND) >= 24 * 7
    assert ttl_for_outcome(FullTextOutcome.NO_OPEN_ACCESS) == 24
    assert ttl_for_outcome(FullTextOutcome.BOT_PROTECTION) >= 24


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1234/abc") == "10.1234/abc"


def test_collect_candidates_provider_first():
    cands = collect_candidates(
        doi="",
        open_access_url="https://example.com/a.pdf",
        source_url="https://example.com/a.pdf",
        db=None,
    )
    assert cands
    assert cands[0].resolver in ("provider", "source_url")
    assert cands[0].url.endswith(".pdf")


def test_collect_candidates_arxiv():
    cands = collect_candidates(arxiv_id="2107.12345", provider="arxiv", db=None)
    assert any(c.resolver == "arxiv" for c in cands)
    assert any("arxiv.org/pdf" in c.url for c in cands)


def test_collect_candidates_pmc():
    cands = collect_candidates(pmcid="PMC123", db=None)
    assert any(c.resolver == "europe_pmc" for c in cands)


@patch("backend.scholarly.uftr.resolve.download_candidate")
@patch("backend.scholarly.uftr.resolve.collect_candidates")
def test_resolve_full_text_found(mock_collect, mock_dl):
    from backend.scholarly.uftr.resolve import resolve_full_text
    from backend.scholarly.uftr.resolvers import Candidate

    mock_collect.return_value = [
        Candidate(url="https://ex.com/p.pdf", resolver="provider"),
    ]
    mock_dl.return_value = (
        FullTextOutcome.FOUND,
        b"%PDF-1.4 x",
        "application/pdf",
        "https://ex.com/p.pdf",
    )
    result = resolve_full_text(open_access_url="https://ex.com/p.pdf", use_cache=False)
    assert result.found
    assert result.full_text_source == "provider"
    assert result.data[:4] == b"%PDF"


@patch("backend.scholarly.uftr.resolve.download_candidate")
@patch("backend.scholarly.uftr.resolve.collect_candidates")
def test_resolve_ranks_bot_over_network(mock_collect, mock_dl):
    from backend.scholarly.uftr.resolve import resolve_full_text
    from backend.scholarly.uftr.resolvers import Candidate

    mock_collect.return_value = [
        Candidate(url="https://a.com/1", resolver="provider"),
        Candidate(url="https://b.com/2", resolver="unpaywall"),
    ]
    mock_dl.side_effect = [
        (FullTextOutcome.NETWORK_ERROR, b"", "", "https://a.com/1"),
        (FullTextOutcome.BOT_PROTECTION, b"<html>", "text/html", "https://b.com/2"),
    ]
    result = resolve_full_text(doi="10.1/x", use_cache=False)
    assert result.outcome == FullTextOutcome.BOT_PROTECTION
    assert not result.found


def test_should_auto_retry_age_gate():
    now = datetime(2026, 8, 4, tzinfo=timezone.utc)
    uf = SimpleNamespace(
        path="",
        size=0,
        fulltext_json='{"last_attempt_at":"2026-08-03T00:00:00+00:00","outcome":"NO_OPEN_ACCESS"}',
    )
    assert should_auto_retry(uf, now=now, min_days=7) is False
    uf.fulltext_json = '{"last_attempt_at":"2026-07-20T00:00:00+00:00","outcome":"NO_OPEN_ACCESS"}'
    assert should_auto_retry(uf, now=now, min_days=7) is True
    assert should_auto_retry(uf, now=now, force=True) is True


def test_should_auto_retry_skips_when_has_pdf():
    uf = SimpleNamespace(
        path="x.pdf",
        size=100,
        fulltext_json="{}",
    )
    assert should_auto_retry(uf, force=True) is False


def test_apply_resolution_persists_attempts():
    uf = SimpleNamespace(fulltext_json="{}")
    result = ResolutionResult(
        outcome=FullTextOutcome.NO_OPEN_ACCESS,
        attempts=[
            ResolutionAttempt(
                resolver="unpaywall",
                outcome=FullTextOutcome.NO_OPEN_ACCESS,
                reason="empty",
            )
        ],
    )
    state = apply_resolution_to_file(uf, result)
    assert state["outcome"] == "NO_OPEN_ACCESS"
    assert uf.fulltext_json
    assert "unpaywall" in uf.fulltext_json


def test_unpaywall_parse_best_oa():
    from backend.scholarly.unpaywall import lookup_oa_pdf_url

    with patch("backend.scholarly.unpaywall.provider_get") as pg:
        pg.return_value = {
            "best_oa_location": {
                "url_for_pdf": "https://oa.example/paper.pdf",
            }
        }
        url = lookup_oa_pdf_url("10.1234/abc", db=None)
        assert url == "https://oa.example/paper.pdf"
