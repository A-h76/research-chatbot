"""Mendeley Connect v1 — OAuth 2.0 + one-shot document import.

Maps Mendeley documents to LibraryRecord and reuses LibraryImportService
(same pipeline as BibTeX / RIS / Zotero). Incremental sync is Phase 1b.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests

from .normalize import LibraryRecord, normalize_doi

logger = logging.getLogger(__name__)

MENDELEY_AUTHORIZE_URL = "https://api.mendeley.com/oauth/authorize"
MENDELEY_TOKEN_URL = "https://api.mendeley.com/oauth/token"
MENDELEY_API = "https://api.mendeley.com"

_MENDELEY_ID_NAMES = ("MENDELEY_CLIENT_ID", "MENDELEY_APP_ID", "MENDELEY_ID")
_MENDELEY_SECRET_NAMES = ("MENDELEY_CLIENT_SECRET", "MENDELEY_APP_SECRET", "MENDELEY_SECRET")


def _env_first(*names: str) -> str:
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        val = str(raw).strip().strip('"').strip("'").strip()
        if val:
            return val
    return ""


def mendeley_configured() -> bool:
    return bool(_env_first(*_MENDELEY_ID_NAMES) and _env_first(*_MENDELEY_SECRET_NAMES))


def mendeley_missing_env() -> list[str]:
    missing: list[str] = []
    if not _env_first(*_MENDELEY_ID_NAMES):
        missing.append("MENDELEY_CLIENT_ID")
    if not _env_first(*_MENDELEY_SECRET_NAMES):
        missing.append("MENDELEY_CLIENT_SECRET")
    return missing


def _client_creds() -> tuple[str, str]:
    return (
        _env_first(*_MENDELEY_ID_NAMES),
        _env_first(*_MENDELEY_SECRET_NAMES),
    )


def begin_oauth(callback_uri: str, state: str) -> dict[str, str]:
    """Return authorize_url for the Authorization Code flow."""
    client_id, _ = _client_creds()
    params = {
        "client_id": client_id,
        "redirect_uri": callback_uri,
        "response_type": "code",
        "scope": "all",
        "state": state,
    }
    return {"authorize_url": f"{MENDELEY_AUTHORIZE_URL}?{urlencode(params)}"}


def finish_oauth(*, code: str, callback_uri: str) -> dict[str, str]:
    """Exchange authorization code for access + refresh tokens."""
    client_id, client_secret = _client_creds()
    r = requests.post(
        MENDELEY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": callback_uri,
        },
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "access_token": str(data.get("access_token") or ""),
        "refresh_token": str(data.get("refresh_token") or ""),
        "expires_in": str(data.get("expires_in") or ""),
        "token_type": str(data.get("token_type") or "bearer"),
    }


def refresh_access_token(refresh_token: str) -> dict[str, str]:
    client_id, client_secret = _client_creds()
    r = requests.post(
        MENDELEY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "access_token": str(data.get("access_token") or ""),
        "refresh_token": str(data.get("refresh_token") or refresh_token),
        "expires_in": str(data.get("expires_in") or ""),
    }


def _api_get(
    path: str,
    access_token: str,
    *,
    accept: str,
    params: dict | None = None,
) -> Any:
    r = requests.get(
        f"{MENDELEY_API}{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": accept,
        },
        params=params or {},
        timeout=30,
    )
    r.raise_for_status()
    if not r.content:
        return []
    return r.json()


def fetch_profile(access_token: str) -> dict[str, str]:
    try:
        data = _api_get(
            "/profiles/me",
            access_token,
            accept="application/vnd.mendeley-profiles.1+json",
        )
    except Exception as exc:
        logger.warning("mendeley profile fetch failed: %s", exc)
        return {"id": "", "display_name": ""}
    if not isinstance(data, dict):
        return {"id": "", "display_name": ""}
    name = data.get("display_name") or ""
    if not name:
        first = (data.get("first_name") or "").strip()
        last = (data.get("last_name") or "").strip()
        name = f"{first} {last}".strip()
    return {
        "id": str(data.get("id") or ""),
        "display_name": name,
    }


def list_folders(access_token: str) -> list[dict]:
    data = _api_get(
        "/folders",
        access_token,
        accept="application/vnd.mendeley-folder.1+json",
        params={"limit": 100},
    )
    out = [{"key": "all", "name": "All documents", "parent": None}]
    for item in data or []:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "key": str(item.get("id") or ""),
                "name": item.get("name") or "Untitled",
                "parent": item.get("parent_id") or None,
            }
        )
    return out


def _authors_str(authors: Any) -> str:
    if not isinstance(authors, list):
        return ""
    parts: list[str] = []
    for a in authors[:20]:
        if not isinstance(a, dict):
            continue
        last = (a.get("last_name") or "").strip()
        first = (a.get("first_name") or "").strip()
        if last and first:
            parts.append(f"{last}, {first}")
        elif last or first:
            parts.append(last or first)
    return "; ".join(parts)


def _parse_document(item: dict[str, Any], *, folder_id: str = "", folder_name: str = "") -> LibraryRecord | None:
    title = (item.get("title") or "").strip()
    identifiers = item.get("identifiers") or {}
    if not isinstance(identifiers, dict):
        identifiers = {}
    doi = normalize_doi(identifiers.get("doi") or item.get("doi") or "")
    if not title and not doi:
        return None

    year = ""
    year_raw = item.get("year")
    if year_raw not in (None, ""):
        year = str(year_raw).strip()[:10]

    websites = item.get("websites") or []
    url = ""
    if isinstance(websites, list) and websites:
        url = str(websites[0] or "").strip()
    if not url:
        url = str(item.get("link") or "").strip()

    tags = ["from-mendeley"]
    for t in item.get("tags") or []:
        if isinstance(t, str) and t.strip():
            tags.append(t.strip()[:40])

    return LibraryRecord(
        title=title,
        authors=_authors_str(item.get("authors")),
        year=year,
        venue=(item.get("source") or item.get("publisher") or "").strip(),
        doi=doi,
        abstract=(item.get("abstract") or "").strip()[:8000],
        url=url,
        entry_type=(item.get("type") or "journal").strip() or "article",
        external_id=str(item.get("id") or ""),
        source="mendeley",
        tags=tags[:30],
        pdf_url="",
        collection_keys=[folder_id] if folder_id and folder_id not in {"all", "", "root"} else [],
        collection_name=folder_name,
    )


def fetch_documents_since(
    access_token: str,
    *,
    modified_since: str | None = None,
    limit: int = 200,
) -> tuple[list[LibraryRecord], str]:
    """Incremental Mendeley fetch.

    ``modified_since`` is an ISO-8601 timestamp from the previous sync.
    Returns (records, new_modified_since_iso).
    """
    from datetime import datetime, timezone

    limit = max(1, min(int(limit or 200), 200))
    params: dict[str, Any] = {"limit": min(limit, 100), "view": "all"}
    if modified_since:
        params["modified_since"] = modified_since

    records: list[LibraryRecord] = []
    marker = None
    newest = modified_since or ""
    for _ in range(3):
        page_params = dict(params)
        if marker:
            page_params["marker"] = marker
        data = _api_get(
            "/documents",
            access_token,
            accept="application/vnd.mendeley-document.1+json",
            params=page_params,
        )
        if not isinstance(data, list) or not data:
            break
        for item in data:
            if not isinstance(item, dict):
                continue
            rec = _parse_document(item)
            if rec:
                records.append(rec)
            # Track latest last_modified if present
            lm = item.get("last_modified") or item.get("modified") or ""
            if isinstance(lm, str) and lm > (newest or ""):
                newest = lm
            if len(records) >= limit:
                break
        if len(records) >= limit or len(data) < page_params["limit"]:
            break
        last_id = data[-1].get("id") if data else None
        if not last_id or last_id == marker:
            break
        marker = last_id

    if not newest:
        newest = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return records[:limit], newest


def list_document_files(access_token: str, document_id: str) -> list[dict[str, str]]:
    """Files attached to a Mendeley document (PDF preferred)."""
    document_id = (document_id or "").strip()
    if not document_id:
        return []
    data = _api_get(
        "/files",
        access_token,
        accept="application/vnd.mendeley-file.1+json",
        params={"document_id": document_id, "limit": 50},
    )
    out: list[dict[str, str]] = []
    for item in data or []:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("id") or "").strip()
        if not fid:
            continue
        ctype = (item.get("mime_type") or item.get("content_type") or "").lower()
        fname = (item.get("file_name") or item.get("filename") or "").strip()
        is_pdf = "pdf" in ctype or fname.lower().endswith(".pdf")
        if not is_pdf:
            continue
        out.append(
            {
                "key": fid,
                "filename": fname or f"{fid}.pdf",
                "content_type": ctype or "application/pdf",
            }
        )
    return out


def download_file_bytes(
    access_token: str,
    file_id: str,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> bytes:
    """Download Mendeley file bytes (follows 303 → S3)."""
    file_id = (file_id or "").strip()
    if not file_id:
        raise ValueError("empty_file_id")
    r = requests.get(
        f"{MENDELEY_API}/files/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=120,
        allow_redirects=True,
    )
    r.raise_for_status()
    data = r.content or b""
    if len(data) > max_bytes:
        raise ValueError(f"file_too_large:{len(data)}")
    if not data:
        raise ValueError("empty_file")
    return data


def pull_pdf_for_document(
    access_token: str,
    document_id: str,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> dict[str, Any] | None:
    files = list_document_files(access_token, document_id)
    if not files:
        return None
    f = files[0]
    raw = download_file_bytes(access_token, f["key"], max_bytes=max_bytes)
    return {
        "external_id": document_id,
        "attachment_key": f["key"],
        "filename": f["filename"],
        "content_type": f["content_type"] or "application/pdf",
        "data": raw,
    }


def fetch_documents(
    access_token: str,
    *,
    folder_id: str = "all",
    folder_name: str = "",
    limit: int = 200,
) -> list[LibraryRecord]:
    """One-shot metadata import. Cap at ``limit`` (default 200)."""
    limit = max(1, min(int(limit or 200), 200))
    params: dict[str, Any] = {"limit": min(limit, 100), "view": "all"}
    path = "/documents"
    if folder_id and folder_id not in {"all", "", "root"}:
        # Folder membership: /folders/{id}/documents
        path = f"/folders/{folder_id}/documents"

    records: list[LibraryRecord] = []
    # Simple pagination via Link / page — Mendeley uses limit + marker sometimes;
    # for Phase 1a we fetch up to ``limit`` with at most 3 pages.
    marker = None
    for _ in range(3):
        page_params = dict(params)
        if marker:
            page_params["marker"] = marker
        data = _api_get(
            path,
            access_token,
            accept="application/vnd.mendeley-document.1+json",
            params=page_params,
        )
        if not isinstance(data, list):
            break
        for item in data:
            if not isinstance(item, dict):
                continue
            rec = _parse_document(item, folder_id=folder_id, folder_name=folder_name)
            if rec:
                records.append(rec)
            if len(records) >= limit:
                return records[:limit]
        if len(data) < page_params["limit"]:
            break
        # Advance marker from last id when present
        last_id = data[-1].get("id") if data else None
        if not last_id or last_id == marker:
            break
        marker = last_id
    return records[:limit]
