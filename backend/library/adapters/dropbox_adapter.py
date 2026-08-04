"""Dropbox ImportAdapter — list folders + PDF file import (#27)."""

from __future__ import annotations

from typing import Any, ClassVar

from backend.library.adapters.base import AdapterCapabilities, ImportAdapter
from backend.library.normalize import LibraryRecord
from backend.library import dropbox as dropbox_mod


class DropboxAdapter(ImportAdapter):
    name: ClassVar[str] = "dropbox"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            oauth=True,
            folder_list=True,
            incremental_sync=False,
            file_import=True,
        )

    def configured(self) -> bool:
        return dropbox_mod.dropbox_configured()

    def list_folders(self, **context: Any) -> list[dict[str, Any]]:
        return dropbox_mod.list_folders(
            context["access_token"],
            parent_id=context.get("parent_id") or "",
        )

    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        access_token = context["access_token"]
        folder_id = (context.get("folder_id") or "").strip()
        if folder_id in ("root",):
            folder_id = ""
        limit = int(context.get("limit") or 50)
        payload = dropbox_mod.list_pdf_files(
            access_token, folder_id=folder_id, limit=limit
        )
        out: list[LibraryRecord] = []
        for item in payload.get("items") or []:
            name = (item.get("name") or "Untitled.pdf").strip()
            title = name.rsplit(".", 1)[0] if name.lower().endswith(".pdf") else name
            out.append(
                LibraryRecord(
                    title=title,
                    source="dropbox",
                    external_id=str(item.get("id") or ""),
                    url="",
                    pdf_url="",
                    tags=["from-dropbox"],
                )
            )
        return out

    def import_files(self, **context: Any) -> dict[str, Any]:
        access_token = context["access_token"]
        item_keys = context.get("item_keys") or []
        max_bytes = int(context.get("max_bytes") or 50 * 1024 * 1024)
        downloaded = []
        skipped = []
        errors = []
        for key in item_keys:
            ext_id = str(key).strip()
            if not ext_id:
                continue
            hit = dropbox_mod.download_file(
                access_token, ext_id, max_bytes=max_bytes
            )
            if not hit:
                skipped.append({"external_id": ext_id, "reason": "download_failed"})
                continue
            data, filename, content_type = hit
            downloaded.append(
                {
                    "external_id": ext_id,
                    "data": data,
                    "filename": filename,
                    "content_type": content_type,
                }
            )
        return {
            "downloaded": downloaded,
            "skipped": skipped,
            "errors": errors,
        }
