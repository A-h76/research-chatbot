"""UFTR Validator — HTTP / MIME / magic / HTML / bot / paywall detection."""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from urllib.parse import urljoin

import requests

from backend.scholarly.uftr.outcomes import FullTextOutcome, content_kind_for_bytes

logger = logging.getLogger(__name__)

_TIMEOUT = float(os.environ.get("UFTR_TIMEOUT_SECONDS", "12"))
_MAILTO = os.environ.get("CROSSREF_MAILTO") or os.environ.get("UNPAYWALL_EMAIL") or "admin@dhund.com"

_BOT_MARKERS = (
    b"cf-browser-verification",
    b"challenge-platform",
    b"just a moment",
    b"enable javascript and cookies",
    b"attention required",
    b"cloudflare",
    b"checking your browser",
    b"ray id",
)

_PAYWALL_MARKERS = (
    b"purchase this article",
    b"buy this article",
    b"institutional access",
    b"subscribe to access",
    b"access options",
    b"get access",
    b"sign in to access",
    b"full text access",
    b"sciencedirect.com/science/article",
)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": f"Dhund/1.0 (Research OS; mailto:{_MAILTO})",
        "Accept": "application/pdf,application/octet-stream,*/*",
    }


def classify_body(data: bytes, content_type: str = "") -> FullTextOutcome | None:
    """Return a failure outcome if body is not usable Research Content, else None."""
    if not data:
        return FullTextOutcome.INVALID_RESPONSE
    kind = content_kind_for_bytes(data)
    if kind == "pdf":
        return None
    # Today UFTR only attaches PDF; HTML/XML are INVALID until importers land.
    ct = (content_type or "").lower()
    sample = data[:12000].lower()
    if any(m in sample for m in _BOT_MARKERS):
        return FullTextOutcome.BOT_PROTECTION
    if "html" in ct or kind == "html":
        if any(m in sample for m in _PAYWALL_MARKERS):
            return FullTextOutcome.PUBLISHER_PAYWALL
        if any(m in sample for m in _BOT_MARKERS):
            return FullTextOutcome.BOT_PROTECTION
        return FullTextOutcome.INVALID_RESPONSE
    if kind in ("xml", "html"):
        return FullTextOutcome.INVALID_RESPONSE
    return FullTextOutcome.INVALID_RESPONSE


def download_candidate(
    url: str,
    *,
    max_bytes: int = 50 * 1024 * 1024,
    session: requests.Session | None = None,
) -> tuple[FullTextOutcome, bytes, str, str]:
    """Fetch URL and validate. Returns (outcome, data, content_type, final_url)."""
    url = (url or "").strip()
    if not url:
        return FullTextOutcome.NO_OPEN_ACCESS, b"", "", ""

    sess = session or requests.Session()
    try:
        resp = sess.get(
            url,
            headers=_headers(),
            timeout=_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
    except requests.Timeout:
        return FullTextOutcome.TIMEOUT, b"", "", url
    except requests.RequestException as exc:
        logger.debug("uftr download network error url=%s: %s", url[:120], exc)
        return FullTextOutcome.NETWORK_ERROR, b"", "", url

    final_url = str(resp.url or url)
    status = int(resp.status_code or 0)
    if status in (401, 402, 403):
        resp.close()
        return FullTextOutcome.PUBLISHER_PAYWALL, b"", "", final_url
    if status == 404:
        resp.close()
        return FullTextOutcome.NO_OPEN_ACCESS, b"", "", final_url
    if status >= 400:
        resp.close()
        return FullTextOutcome.NETWORK_ERROR, b"", "", final_url

    ctype = (resp.headers.get("Content-Type") or "").lower()
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                resp.close()
                return FullTextOutcome.INVALID_RESPONSE, b"", ctype, final_url
            chunks.append(chunk)
    except requests.Timeout:
        resp.close()
        return FullTextOutcome.TIMEOUT, b"", ctype, final_url
    except Exception as exc:
        resp.close()
        logger.debug("uftr stream error url=%s: %s", final_url[:120], exc)
        return FullTextOutcome.NETWORK_ERROR, b"", ctype, final_url
    finally:
        try:
            resp.close()
        except Exception:
            pass

    data = b"".join(chunks)
    fail = classify_body(data, ctype)
    if fail is None:
        return FullTextOutcome.FOUND, data, ctype, final_url

    # HTML interstitial with a .pdf href — one follow
    if fail == FullTextOutcome.INVALID_RESPONSE and b"href" in data[:20000].lower():
        m = re.search(br'href=["\']([^"\']+\.pdf[^"\']*)["\']', data[:30000], re.I)
        if m:
            next_url = urljoin(final_url, m.group(1).decode("utf-8", "ignore"))
            if next_url and next_url != final_url:
                return download_candidate(next_url, max_bytes=max_bytes, session=sess)

    return fail, data, ctype, final_url


def filename_from_url(url: str, *, fallback: str = "fulltext.pdf") -> str:
    path = (url or "").split("?")[0].rstrip("/")
    name = path.rsplit("/", 1)[-1] if path else ""
    if name.lower().endswith(".pdf") and len(name) < 200:
        return name
    return fallback
