"""Mendeley ImportAdapter — thin wrapper over mendeley.py."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from backend.library.adapters.base import AdapterCapabilities, ImportAdapter
from backend.library import mendeley as mendeley_mod
from backend.library.normalize import LibraryRecord


class MendeleyAdapter(ImportAdapter):
    name: ClassVar[str] = "mendeley"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(oauth=True, folder_list=True, incremental_sync=True)

    def configured(self) -> bool:
        return mendeley_mod.mendeley_configured()

    def list_folders(self, **context: Any) -> list[dict[str, Any]]:
        return mendeley_mod.list_folders(context["access_token"])

    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        folder_id = (context.get("folder_id") or context.get("collection_key") or "all").strip()
        folder_name = context.get("folder_name") or context.get("collection_name") or ""
        limit = int(context.get("limit") or 200)
        return mendeley_mod.fetch_documents(
            context["access_token"],
            folder_id=folder_id,
            folder_name=folder_name,
            limit=limit,
        )

    def synchronize(self, **context: Any) -> dict[str, Any]:
        cursor_raw = context.get("sync_cursor") or ""
        modified_since = None
        try:
            parsed = json.loads(cursor_raw) if cursor_raw.strip().startswith("{") else {}
            modified_since = parsed.get("modified_since") or None
        except Exception:
            if cursor_raw and "T" in cursor_raw:
                modified_since = cursor_raw
        limit = int(context.get("limit") or 200)
        records, newest = mendeley_mod.fetch_documents_since(
            context["access_token"],
            modified_since=modified_since,
            limit=limit,
        )
        return {
            "records": records,
            "sync_cursor": json.dumps({"modified_since": newest}),
            "since": modified_since or "",
            "fetched": len(records),
        }
