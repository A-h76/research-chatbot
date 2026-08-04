"""OneDrive connector — Microsoft Graph OAuth + PDF list/download (#28).

Minimal scope (Golden Rule of Acquisition):
  Connect → browse PDFs → import bytes → apply_pdf_bytes_to_stub → enqueue import
  → Paper Analysis 2.0 → Evidence → Writing (same pipeline as upload / Drive / Dropbox).

Folder watch / delta deferred.

Env:
  ONEDRIVE_CLIENT_ID / ONEDRIVE_CLIENT_SECRET
  (aliases: MICROSOFT_CLIENT_ID / MICROSOFT_CLIENT_SECRET)
Redirect must match APP_BASE_URL + /api/library/onedrive/callback
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

_AUTH_BASE = os.environ.get(
    "ONEDRIVE_AUTH_BASE", "https://login.microsoftonline.com/common/oauth2/v2.0"
).rstrip("/")
GRAPH = os.environ.get("ONEDRIVE_GRAPH_BASE", "https://graph.microsoft.com/v1.0").rstrip("/")

_SCOPES = " ".join(
    [
        "offline_access",
        "openid",
        "profile",
        "User.Read",
        "Files.Read",
    ]
)

_ID_NAMES = ("ONEDRIVE_CLIENT_ID", "MICROSOFT_CLIENT_ID")
_SECRET_NAMES = ("ONEDRIVE_CLIENT_SECRET", "MICROSOFT_CLIENT_SECRET")


def _env_first(*names: str) -> str:
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        val = str(raw).strip().strip('"').strip("'").strip()
        if val:
            return val
    return ""


def onedrive_configured() -> bool:
    return bool(_env_first(*_ID_NAMES) and _env_first(*_SECRET_NAMES))


def onedrive_missing_env() -> list[str]:
    missing: list[str] = []
    if not _env_first(*_ID_NAMES):
        missing.append("ONEDRIVE_CLIENT_ID (or MICROSOFT_CLIENT_ID)")
    if not _env_first(*_SECRET_NAMES):
        missing.append("ONEDRIVE_CLIENT_SECRET (or MICROSOFT_CLIENT_SECRET)")
    return missing


def oauth_redirect_uri(app_base_url: str | None = None) -> str:
    base = (
        app_base_url or os.environ.get("APP_BASE_URL") or "http://localhost:5000"
    ).strip().rstrip("/")
    return f"{base}/api/library/onedrive/callback"


def _client_creds() -> tuple[str, str]:
    return _env_first(*_ID_NAMES), _env_first(*_SECRET_NAMES)


def begin_oauth(callback_uri: str, state: str) -> dict[str, str]:
    client_id, _ = _client_creds()
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": callback_uri,
        "response_mode": "query",
        "scope": _SCOPES,
        "state": state,
    }
    return {"authorize_url": f"{_AUTH_BASE}/authorize?{urlencode(params)}"}


def finish_oauth(*, code: str, callback_uri: str) -> dict[str, str]:
    client_id, client_secret = _client_creds()
    r = requests.post(
        f"{_AUTH_BASE}/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": callback_uri,
            "grant_type": "authorization_code",
            "scope": _SCOPES,
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
        f"{_AUTH_BASE}/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": _SCOPES,
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
            f"{GRAPH}/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("onedrive profile fetch failed: %s", exc)
        return {"id": "", "display_name": "", "email": ""}
    return {
        "id": str(data.get("id") or ""),
        "display_name": str(data.get("displayName") or data.get("userPrincipalName") or ""),
        "email": str(data.get("mail") or data.get("userPrincipalName") or ""),
    }


def _api_get(path: str, access_token: str, *, params: dict | None = None) -> Any:
    r = requests.get(
        f"{GRAPH}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def list_folders(access_token: str, *, parent_id: str = "root") -> list[dict[str, Any]]:
    parent = (parent_id or "root").strip() or "root"
    if parent == "root":
        path = "/me/drive/root/children"
    else:
        path = f"/me/drive/items/{parent}/children"
    data = _api_get(
        path,
        access_token,
        params={"$top": "100", "$select": "id,name,folder,parentReference"},
    )
    out = [{"key": "root", "name": "OneDrive", "parent": None}]
    for item in data.get("value") or []:
        if not isinstance(item, dict) or not item.get("folder"):
            continue
        out.append(
            {
                "key": str(item.get("id") or ""),
                "name": item.get("name") or "Untitled",
                "parent": parent,
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
    """List PDF files in a OneDrive folder (root by default)."""
    folder = (folder_id or "root").strip() or "root"
    limit = max(1, min(int(limit or 50), 100))

    if page_token:
        # Graph nextLink is a full URL — fetch directly
        r = requests.get(
            page_token,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    else:
        if folder == "root":
            path = "/me/drive/root/children"
        else:
            path = f"/me/drive/items/{folder}/children"
        data = _api_get(
            path,
            access_token,
            params={
                "$top": str(limit),
                "$select": "id,name,size,file,lastModifiedDateTime,webUrl",
                "$orderby": "lastModifiedDateTime desc",
            },
        )

    items = []
    for f in data.get("value") or []:
        if not isinstance(f, dict):
            continue
        file_meta = f.get("file") or {}
        mime = (file_meta.get("mimeType") or "").lower() if isinstance(file_meta, dict) else ""
        name = (f.get("name") or "").strip()
        if not name.lower().endswith(".pdf") and "pdf" not in mime:
            continue
        items.append(
            {
                "id": str(f.get("id") or ""),
                "name": name or "Untitled.pdf",
                "mime_type": mime or "application/pdf",
                "size": int(f.get("size") or 0),
                "modified_time": str(f.get("lastModifiedDateTime") or ""),
                "web_view_link": str(f.get("webUrl") or ""),
            }
        )
        if len(items) >= limit:
            break

    return {
        "items": items,
        "next_page_token": str(data.get("@odata.nextLink") or ""),
        "folder_id": folder,
    }


def download_file(
    access_token: str,
    file_id: str,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str, str] | None:
    """Download a OneDrive file. Returns (bytes, filename, content_type) or None."""
    file_id = (file_id or "").strip()
    if not file_id:
        return None
    try:
        meta = _api_get(
            f"/me/drive/items/{file_id}",
            access_token,
            params={"$select": "id,name,size,file"},
        )
    except Exception as exc:
        logger.warning("onedrive meta failed file_id=%s: %s", file_id, exc)
        return None

    name = (meta.get("name") or "attachment.pdf").strip() or "attachment.pdf"
    size_hint = int(meta.get("size") or 0)
    if size_hint and size_hint > max_bytes:
        logger.info("onedrive file too large file_id=%s size=%s", file_id, size_hint)
        return None
    file_meta = meta.get("file") or {}
    mime = (file_meta.get("mimeType") or "").lower() if isinstance(file_meta, dict) else ""
    if mime and "pdf" not in mime and not name.lower().endswith(".pdf"):
        logger.info("onedrive skip non-pdf file_id=%s mime=%s", file_id, mime)
        return None

    try:
        r = requests.get(
            f"{GRAPH}/me/drive/items/{file_id}/content",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
            stream=True,
            allow_redirects=True,
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
        if not data or data[:4] != b"%PDF":
            logger.info("onedrive download not PDF magic file_id=%s", file_id)
            return None
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return data, name[:300], "application/pdf"
    except Exception as exc:
        logger.warning("onedrive download failed file_id=%s: %s", file_id, exc)
        return None
