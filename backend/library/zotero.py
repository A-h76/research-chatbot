"""Zotero Connect v1 — OAuth 1.0a + collection/item import.

Uses Authlib when credentials are configured. Import maps to LibraryRecord
and reuses LibraryImportService (same pipeline as BibTeX/RIS).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .normalize import LibraryRecord, normalize_doi

logger = logging.getLogger(__name__)

ZOTERO_REQUEST_TOKEN_URL = "https://www.zotero.org/oauth/request"
ZOTERO_AUTHORIZE_URL = "https://www.zotero.org/oauth/authorize"
ZOTERO_ACCESS_TOKEN_URL = "https://www.zotero.org/oauth/access"
ZOTERO_API = "https://api.zotero.org"

# Primary names match https://www.zotero.org/oauth/apps (“Client Key / Secret”).
# Aliases cover common paste mistakes from other Zotero API docs.
_ZOTERO_KEY_NAMES = ("ZOTERO_CLIENT_KEY", "ZOTERO_CLIENT_ID", "ZOTERO_API_KEY")
_ZOTERO_SECRET_NAMES = ("ZOTERO_CLIENT_SECRET", "ZOTERO_API_SECRET")


def _env_first(*names: str) -> str:
    """First non-empty env value; strips whitespace and wrapping quotes."""
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        val = str(raw).strip().strip('"').strip("'").strip()
        if val:
            return val
    return ""


def zotero_configured() -> bool:
    return bool(_env_first(*_ZOTERO_KEY_NAMES) and _env_first(*_ZOTERO_SECRET_NAMES))


def zotero_missing_env() -> list[str]:
    """Which primary env vars are empty (for UI / ops; never returns secrets)."""
    missing: list[str] = []
    if not _env_first(*_ZOTERO_KEY_NAMES):
        missing.append("ZOTERO_CLIENT_KEY")
    if not _env_first(*_ZOTERO_SECRET_NAMES):
        missing.append("ZOTERO_CLIENT_SECRET")
    return missing


def _client_creds() -> tuple[str, str]:
    return (
        _env_first(*_ZOTERO_KEY_NAMES),
        _env_first(*_ZOTERO_SECRET_NAMES),
    )


def _oauth1_session(token=None, token_secret=None, callback_uri=None):
    from authlib.integrations.requests_client import OAuth1Session

    key, secret = _client_creds()
    kwargs = {}
    if callback_uri:
        kwargs["redirect_uri"] = callback_uri
    return OAuth1Session(
        key,
        secret,
        token=token,
        token_secret=token_secret,
        **kwargs,
    )


def begin_oauth(callback_uri: str) -> dict[str, str]:
    """Return request_token, request_token_secret, authorize_url."""
    sess = _oauth1_session(callback_uri=callback_uri)
    # library_access + write=0 — read-only import
    token = sess.fetch_request_token(
        ZOTERO_REQUEST_TOKEN_URL,
        params={"library_access": "1", "write_access": "0"},
    )
    auth_url = sess.create_authorization_url(ZOTERO_AUTHORIZE_URL)
    return {
        "request_token": token.get("oauth_token", ""),
        "request_token_secret": token.get("oauth_token_secret", ""),
        "authorize_url": auth_url[0] if isinstance(auth_url, tuple) else auth_url,
    }


def finish_oauth(
    *,
    request_token: str,
    request_token_secret: str,
    oauth_verifier: str,
    callback_uri: str,
) -> dict[str, str]:
    sess = _oauth1_session(
        token=request_token,
        token_secret=request_token_secret,
        callback_uri=callback_uri,
    )
    token = sess.fetch_access_token(
        ZOTERO_ACCESS_TOKEN_URL,
        verifier=oauth_verifier,
    )
    # Zotero also returns userID + username as query-style extras on some clients;
    # Authlib puts them in the token dict when present.
    return {
        "access_token": token.get("oauth_token", ""),
        "access_secret": token.get("oauth_token_secret", ""),
        "user_id": str(token.get("userID") or token.get("userId") or ""),
        "username": str(token.get("username") or ""),
    }


def _api_get(
    path: str,
    access_token: str,
    access_secret: str,
    params: dict | None = None,
    *,
    return_headers: bool = False,
) -> Any:
    sess = _oauth1_session(token=access_token, token_secret=access_secret)
    url = f"{ZOTERO_API}{path}"
    r = sess.get(url, params=params or {}, timeout=30)
    r.raise_for_status()
    if not r.content:
        data: Any = [] if not return_headers else ([], {})
        return data
    body = r.json()
    if return_headers:
        return body, dict(r.headers)
    return body


def fetch_items_since(
    access_token: str,
    access_secret: str,
    zotero_user_id: str,
    *,
    since_version: int = 0,
    limit: int = 200,
) -> tuple[list[LibraryRecord], int]:
    """Incremental fetch using Zotero ``since`` library version.

    Returns (records, new_library_version). When ``since_version`` is 0,
    behaves like a capped first sync of top-level items.
    """
    since_version = max(0, int(since_version or 0))
    limit = max(1, min(int(limit or 200), 500))
    path = f"/users/{zotero_user_id}/items/top"
    params: dict[str, Any] = {
        "limit": min(limit, 100),
        "format": "json",
        "since": since_version,
    }
    data, headers = _api_get(
        path, access_token, access_secret, params=params, return_headers=True
    )
    new_version = since_version
    try:
        new_version = int(headers.get("Last-Modified-Version") or headers.get("last-modified-version") or since_version)
    except (TypeError, ValueError):
        new_version = since_version

    records: list[LibraryRecord] = []
    for item in data or []:
        rec = _item_to_record(item)
        if rec:
            records.append(rec)
        if len(records) >= limit:
            break

    # If first page filled and we still need more, page with start
    start = len(data or [])
    while len(records) < limit and start > 0 and len(data or []) >= params["limit"]:
        page_params = dict(params)
        page_params["start"] = start
        data2, headers2 = _api_get(
            path, access_token, access_secret, params=page_params, return_headers=True
        )
        try:
            v2 = int(headers2.get("Last-Modified-Version") or new_version)
            new_version = max(new_version, v2)
        except (TypeError, ValueError):
            pass
        if not data2:
            break
        for item in data2:
            rec = _item_to_record(item)
            if rec:
                records.append(rec)
            if len(records) >= limit:
                break
        start += len(data2)
        if len(data2) < params["limit"]:
            break

    return records[:limit], max(new_version, since_version)


def list_collections(access_token: str, access_secret: str, zotero_user_id: str) -> list[dict]:
    data = _api_get(
        f"/users/{zotero_user_id}/collections",
        access_token,
        access_secret,
        params={"limit": 100},
    )
    out = [{"key": "all", "name": "All items", "parent": None}]
    for item in data or []:
        data_obj = item.get("data") or item
        out.append(
            {
                "key": data_obj.get("key") or item.get("key"),
                "name": data_obj.get("name") or "Untitled",
                "parent": data_obj.get("parentCollection") or None,
            }
        )
    return out


def _creators_to_authors(creators: list) -> str:
    parts = []
    for c in creators or []:
        if c.get("name"):
            parts.append(c["name"])
            continue
        last = (c.get("lastName") or "").strip()
        first = (c.get("firstName") or "").strip()
        if last and first:
            parts.append(f"{last}, {first}")
        elif last:
            parts.append(last)
    return "; ".join(parts)


def _item_to_record(item: dict) -> LibraryRecord | None:
    data = item.get("data") or item
    item_type = (data.get("itemType") or "").lower()
    if item_type in {"attachment", "note", "annotation"}:
        return None
    title = (data.get("title") or "").strip()
    doi = normalize_doi(data.get("DOI") or data.get("doi") or "")
    if not title and not doi:
        return None
    year = ""
    date = data.get("date") or data.get("issueDate") or ""
    import re

    m = re.search(r"(19|20)\d{2}", date)
    if m:
        year = m.group(0)
    venue = (
        data.get("publicationTitle")
        or data.get("bookTitle")
        or data.get("proceedingsTitle")
        or data.get("university")
        or ""
    )
    url = data.get("url") or ""
    abstract = data.get("abstractNote") or ""
    tags = ["from-zotero"] + [f"kw:{(t.get('tag') if isinstance(t, dict) else t)}" for t in (data.get("tags") or [])[:8]]
    coll_keys = [str(k) for k in (data.get("collections") or []) if k]
    return LibraryRecord(
        title=title,
        authors=_creators_to_authors(data.get("creators") or []),
        year=year,
        venue=(venue or "")[:300],
        doi=doi,
        abstract=abstract,
        url=url,
        entry_type="article",
        external_id=str(data.get("key") or item.get("key") or ""),
        source="zotero",
        tags=[t for t in tags if t and not t.endswith(":")],
        collection_keys=coll_keys,
    )


def fetch_items(
    access_token: str,
    access_secret: str,
    zotero_user_id: str,
    *,
    collection_key: str | None = None,
    collection_name: str = "",
    limit: int = 200,
) -> list[LibraryRecord]:
    if collection_key and collection_key not in {"all", "", "root"}:
        path = f"/users/{zotero_user_id}/collections/{collection_key}/items/top"
    else:
        path = f"/users/{zotero_user_id}/items/top"
    data = _api_get(
        path,
        access_token,
        access_secret,
        params={"limit": min(limit, 100), "format": "json"},
    )
    records: list[LibraryRecord] = []
    for item in data or []:
        rec = _item_to_record(item)
        if rec:
            if collection_key and collection_key not in {"all", "", "root"}:
                if collection_key not in rec.collection_keys:
                    rec.collection_keys = list(rec.collection_keys) + [collection_key]
                if collection_name:
                    rec.collection_name = collection_name
            records.append(rec)
        if len(records) >= limit:
            break
    return records


def parse_oauth_callback_args(args: dict) -> dict[str, str]:
    """Normalize Flask request.args for Zotero callback."""
    return {
        "oauth_token": (args.get("oauth_token") or "").strip(),
        "oauth_verifier": (args.get("oauth_verifier") or "").strip(),
    }
