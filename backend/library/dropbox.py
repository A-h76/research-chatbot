"""Dropbox connector — OAuth 2.0 + PDF list/download (#27).

Minimal scope (Golden Rule of Acquisition):
  Connect → browse PDFs → import bytes → apply_pdf_bytes_to_stub → enqueue import
  → Paper Analysis 2.0 → Evidence → Writing (same pipeline as upload / Drive).

Folder watch / webhooks deferred.

Env:
  DROPBOX_CLIENT_ID / DROPBOX_CLIENT_SECRET
Redirect must match APP_BASE_URL + /api/library/dropbox/callback
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

DROPBOX_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
DROPBOX_API = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT = "https://content.dropboxapi.com/2"

# Scoped app: metadata + content read + account identity for display.
_SCOPES = " ".join(
    [
        "account_info.read",
        "files.metadata.read",
        "files.content.read",
    ]
)


def _env(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None:
        return ""
    return str(raw).strip().strip('"').strip("'").strip()


def dropbox_configured() -> bool:
    return bool(_env("DROPBOX_CLIENT_ID") and _env("DROPBOX_CLIENT_SECRET"))


def dropbox_missing_env() -> list[str]:
    missing: list[str] = []
    if not _env("DROPBOX_CLIENT_ID"):
        missing.append("DROPBOX_CLIENT_ID")
    if not _env("DROPBOX_CLIENT_SECRET"):
        missing.append("DROPBOX_CLIENT_SECRET")
    return missing


def oauth_redirect_uri(app_base_url: str | None = None) -> str:
    base = (
        app_base_url or os.environ.get("APP_BASE_URL") or "http://localhost:5000"
    ).strip().rstrip("/")
    return f"{base}/api/library/dropbox/callback"


def _client_creds() -> tuple[str, str]:
    return _env("DROPBOX_CLIENT_ID"), _env("DROPBOX_CLIENT_SECRET")


def begin_oauth(callback_uri: str, state: str) -> dict[str, str]:
    client_id, _ = _client_creds()
    params = {
        "client_id": client_id,
        "redirect_uri": callback_uri,
        "response_type": "code",
        "token_access_type": "offline",
        "state": state,
        "scope": _SCOPES,
    }
    return {"authorize_url": f"{DROPBOX_AUTH_URL}?{urlencode(params)}"}


def finish_oauth(*, code: str, callback_uri: str) -> dict[str, str]:
    client_id, client_secret = _client_creds()
    r = requests.post(
        DROPBOX_TOKEN_URL,
        data={
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": callback_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
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
        DROPBOX_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
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


def fetch_profile(access_token: str) -> dict[str, str]:
    try:
        r = requests.post(
            f"{DROPBOX_API}/users/get_current_account",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            data="null",
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("dropbox profile fetch failed: %s", exc)
        return {"id": "", "display_name": "", "email": ""}
    name = data.get("name") or {}
    display = (
        (name.get("display_name") if isinstance(name, dict) else "")
        or data.get("email")
        or ""
    )
    return {
        "id": str(data.get("account_id") or ""),
        "display_name": str(display or ""),
        "email": str(data.get("email") or ""),
    }


def _api_post(path: str, access_token: str, body: Any) -> Any:
    r = requests.post(
        f"{DROPBOX_API}{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def list_folders(access_token: str, *, parent_id: str = "") -> list[dict[str, Any]]:
    """List immediate child folders. parent_id '' = Dropbox root."""
    path = (parent_id or "").strip()
    if path in ("root", "/"):
        path = ""
    data = _api_post(
        "/files/list_folder",
        access_token,
        {"path": path, "limit": 100, "include_non_downloadable_files": False},
    )
    out = [{"key": "", "name": "Dropbox", "parent": None}]
    for entry in data.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get(".tag") != "folder":
            continue
        out.append(
            {
                "key": str(entry.get("path_lower") or entry.get("id") or ""),
                "name": entry.get("name") or "Untitled",
                "parent": path or "",
            }
        )
    return out


def list_pdf_files(
    access_token: str,
    *,
    folder_id: str = "",
    limit: int = 50,
    page_token: str = "",
) -> dict[str, Any]:
    """List PDF files in a folder (Dropbox root by default)."""
    path = (folder_id or "").strip()
    if path in ("root", "/"):
        path = ""
    limit = max(1, min(int(limit or 50), 100))

    if page_token:
        data = _api_post(
            "/files/list_folder/continue",
            access_token,
            {"cursor": page_token},
        )
    else:
        data = _api_post(
            "/files/list_folder",
            access_token,
            {
                "path": path,
                "limit": limit,
                "include_non_downloadable_files": False,
            },
        )

    items = []
    for entry in data.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get(".tag") != "file":
            continue
        name = (entry.get("name") or "").strip()
        if not name.lower().endswith(".pdf"):
            continue
        items.append(
            {
                "id": str(entry.get("id") or ""),
                "name": name or "Untitled.pdf",
                "mime_type": "application/pdf",
                "size": int(entry.get("size") or 0),
                "modified_time": str(
                    entry.get("client_modified") or entry.get("server_modified") or ""
                ),
                "web_view_link": "",
                "path": str(entry.get("path_display") or entry.get("path_lower") or ""),
            }
        )
        if len(items) >= limit:
            break

    next_token = ""
    if data.get("has_more") and data.get("cursor"):
        next_token = str(data.get("cursor") or "")

    return {
        "items": items,
        "next_page_token": next_token,
        "folder_id": path or "root",
    }


def download_file(
    access_token: str,
    file_id: str,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str, str] | None:
    """Download a Dropbox file by id (id:…) or path. Returns (bytes, filename, content_type)."""
    file_id = (file_id or "").strip()
    if not file_id:
        return None
    # Prefer id: form; accept path_display as fallback
    path_arg = file_id if file_id.startswith("id:") or file_id.startswith("/") else file_id
    try:
        r = requests.post(
            f"{DROPBOX_CONTENT}/files/download",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Dropbox-API-Arg": json.dumps({"path": path_arg}),
            },
            timeout=60,
            stream=True,
        )
        r.raise_for_status()
        # Filename from Dropbox-API-Result header when present
        name = "attachment.pdf"
        result_hdr = r.headers.get("Dropbox-API-Result") or ""
        if result_hdr:
            try:
                meta = json.loads(result_hdr)
                name = (meta.get("name") or name).strip() or name
            except Exception:
                pass

        chunks: list[bytes] = []
        total = 0
        for chunk in r.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
        if not data or data[:4] != b"%PDF":
            logger.info("dropbox download not PDF magic path=%s", path_arg[:80])
            return None
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return data, name[:300], "application/pdf"
    except Exception as exc:
        logger.warning("dropbox download failed path=%s: %s", path_arg[:80], exc)
        return None
