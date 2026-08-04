"""Google Drive connector — OAuth 2.0 + PDF list/download.

Minimal #23 scope (Golden Rule):
  Connect → browse PDFs → import bytes → apply_pdf_bytes_to_stub → enqueue import
  → Paper Analysis 2.0 → Evidence (same pipeline as upload).

Folder watch / Changes API deferred.

Env (prefer dedicated Drive client; fall back to login Google client):
  GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET
  or GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
Redirect must match APP_BASE_URL + /api/library/google_drive/callback
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DRIVE_API = "https://www.googleapis.com/drive/v3"

# Readonly Drive + identity for display name (separate from login session scopes).
_SCOPES = " ".join(
    [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
)

_ID_NAMES = (
    "GOOGLE_DRIVE_CLIENT_ID",
    "GOOGLE_CLIENT_ID",
)
_SECRET_NAMES = (
    "GOOGLE_DRIVE_CLIENT_SECRET",
    "GOOGLE_CLIENT_SECRET",
)


def _env_first(*names: str) -> str:
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        val = str(raw).strip().strip('"').strip("'").strip()
        if val:
            return val
    return ""


def drive_configured() -> bool:
    return bool(_env_first(*_ID_NAMES) and _env_first(*_SECRET_NAMES))


def drive_missing_env() -> list[str]:
    missing: list[str] = []
    if not _env_first(*_ID_NAMES):
        missing.append("GOOGLE_DRIVE_CLIENT_ID (or GOOGLE_CLIENT_ID)")
    if not _env_first(*_SECRET_NAMES):
        missing.append("GOOGLE_DRIVE_CLIENT_SECRET (or GOOGLE_CLIENT_SECRET)")
    return missing


def oauth_redirect_uri(app_base_url: str | None = None) -> str:
    """Authorized redirect URI — must match Google Cloud Console exactly."""
    base = (app_base_url or os.environ.get("APP_BASE_URL") or "http://localhost:5000").strip().rstrip("/")
    redirect_uri = f"{base}/api/library/google_drive/callback"
    return redirect_uri


def _client_creds() -> tuple[str, str]:
    return _env_first(*_ID_NAMES), _env_first(*_SECRET_NAMES)


def begin_oauth(callback_uri: str, state: str) -> dict[str, str]:
    client_id, _ = _client_creds()
    params = {
        "client_id": client_id,
        "redirect_uri": callback_uri,
        "response_type": "code",
        "scope": _SCOPES,
        "state": state,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    return {"authorize_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}"}


def finish_oauth(*, code: str, callback_uri: str) -> dict[str, str]:
    client_id, client_secret = _client_creds()
    r = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
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
        GOOGLE_TOKEN_URL,
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
        r = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("google drive profile fetch failed: %s", exc)
        return {"id": "", "display_name": "", "email": ""}
    return {
        "id": str(data.get("sub") or data.get("id") or ""),
        "display_name": str(data.get("name") or data.get("email") or ""),
        "email": str(data.get("email") or ""),
    }


def _api_get(path: str, access_token: str, *, params: dict | None = None) -> Any:
    r = requests.get(
        f"{DRIVE_API}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def list_folders(access_token: str, *, parent_id: str = "root") -> list[dict[str, Any]]:
    parent = (parent_id or "root").strip() or "root"
    q = (
        f"'{parent}' in parents and trashed=false and "
        "mimeType='application/vnd.google-apps.folder'"
    )
    data = _api_get(
        "/files",
        access_token,
        params={
            "q": q,
            "pageSize": 100,
            "fields": "files(id,name,parents)",
            "orderBy": "name",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        },
    )
    out = [{"key": "root", "name": "My Drive", "parent": None}]
    for item in data.get("files") or []:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "key": str(item.get("id") or ""),
                "name": item.get("name") or "Untitled",
                "parent": parent if parent != "root" else "root",
            }
        )
    return out


def list_pdf_files(
    access_token: str,
    *,
    folder_id: str = "root",
    limit: int = 50,
    page_token: str = "",
) -> dict[str, Any]:
    """List PDF files in a folder (My Drive root by default)."""
    folder = (folder_id or "root").strip() or "root"
    limit = max(1, min(int(limit or 50), 100))
    q = (
        f"'{folder}' in parents and trashed=false and "
        "mimeType='application/pdf'"
    )
    params: dict[str, Any] = {
        "q": q,
        "pageSize": limit,
        "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,webViewLink,parents)",
        "orderBy": "modifiedTime desc",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
    }
    if page_token:
        params["pageToken"] = page_token
    data = _api_get("/files", access_token, params=params)
    items = []
    for f in data.get("files") or []:
        if not isinstance(f, dict):
            continue
        items.append(
            {
                "id": str(f.get("id") or ""),
                "name": f.get("name") or "Untitled.pdf",
                "mime_type": f.get("mimeType") or "application/pdf",
                "size": int(f.get("size") or 0),
                "modified_time": f.get("modifiedTime") or "",
                "web_view_link": f.get("webViewLink") or "",
            }
        )
    return {
        "items": items,
        "next_page_token": data.get("nextPageToken") or "",
        "folder_id": folder,
    }


def download_file(
    access_token: str,
    file_id: str,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str, str] | None:
    """Download a Drive file. Returns (bytes, filename, content_type) or None."""
    file_id = (file_id or "").strip()
    if not file_id:
        return None
    try:
        meta = _api_get(
            f"/files/{file_id}",
            access_token,
            params={
                "fields": "id,name,mimeType,size",
                "supportsAllDrives": "true",
            },
        )
    except Exception as exc:
        logger.warning("drive meta failed file_id=%s: %s", file_id, exc)
        return None

    mime = (meta.get("mimeType") or "").lower()
    name = (meta.get("name") or "attachment.pdf").strip() or "attachment.pdf"
    size_hint = int(meta.get("size") or 0)
    if size_hint and size_hint > max_bytes:
        logger.info("drive file too large file_id=%s size=%s", file_id, size_hint)
        return None
    if mime and "pdf" not in mime and mime != "application/octet-stream":
        # Only PDF for Golden Rule path in #23
        logger.info("drive skip non-pdf file_id=%s mime=%s", file_id, mime)
        return None

    try:
        r = requests.get(
            f"{DRIVE_API}/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"alt": "media", "supportsAllDrives": "true"},
            timeout=60,
            stream=True,
        )
        r.raise_for_status()
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
        if not data:
            return None
        if data[:4] != b"%PDF" and "pdf" in mime:
            # still accept if Google said pdf
            pass
        elif data[:4] != b"%PDF":
            logger.info("drive download not PDF magic file_id=%s", file_id)
            return None
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return data, name[:300], "application/pdf"
    except Exception as exc:
        logger.warning("drive download failed file_id=%s: %s", file_id, exc)
        return None
