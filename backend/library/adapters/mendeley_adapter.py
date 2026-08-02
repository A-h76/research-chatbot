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
        return AdapterCapabilities(
            oauth=True, folder_list=True, incremental_sync=True, file_import=True
        )

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

    def import_files(self, **context: Any) -> dict[str, Any]:
        item_keys = context.get("item_keys") or []
        if isinstance(item_keys, str):
            item_keys = [item_keys]
        single = (context.get("external_id") or context.get("item_key") or "").strip()
        if single and single not in item_keys:
            item_keys = list(item_keys) + [single]
        max_bytes = int(context.get("max_bytes") or 50 * 1024 * 1024)
        downloaded: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        token = context["access_token"]
        for key in item_keys:
            key = str(key or "").strip()
            if not key:
                continue
            try:
                hit = mendeley_mod.pull_pdf_for_document(
                    token, key, max_bytes=max_bytes
                )
                if hit:
                    downloaded.append(hit)
                else:
                    skipped.append({"external_id": key, "reason": "no_pdf"})
            except Exception as exc:
                errors.append({"external_id": key, "error": str(exc)[:200]})
        return {
            "downloaded": downloaded,
            "skipped": skipped,
            "errors": errors,
            "provider": "mendeley",
        }
