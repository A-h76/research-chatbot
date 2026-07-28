"""Concrete ImportAdapter wrappers for Phase 1a/1b Bridge connectors."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from backend.library.adapters.base import AdapterCapabilities, ImportAdapter
from backend.library.bibtex import parse_bibtex
from backend.library.normalize import LibraryRecord
from backend.library.ris import parse_ris
from backend.library import zotero as zotero_mod


class BibTeXAdapter(ImportAdapter):
    name: ClassVar[str] = "bibtex"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(file_parse=True)

    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        text = context.get("text") or context.get("content") or ""
        return parse_bibtex(str(text))


class RISAdapter(ImportAdapter):
    name: ClassVar[str] = "ris"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(file_parse=True)

    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        text = context.get("text") or context.get("content") or ""
        return parse_ris(str(text))


class ZoteroAdapter(ImportAdapter):
    name: ClassVar[str] = "zotero"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(oauth=True, folder_list=True, incremental_sync=True)

    def configured(self) -> bool:
        return zotero_mod.zotero_configured()

    def list_folders(self, **context: Any) -> list[dict[str, Any]]:
        return zotero_mod.list_collections(
            context["access_token"],
            context["access_secret"],
            context["external_user_id"],
        )

    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        collection_key = (context.get("collection_key") or "all").strip()
        collection_name = context.get("collection_name") or ""
        limit = int(context.get("limit") or 200)
        return zotero_mod.fetch_items(
            context["access_token"],
            context["access_secret"],
            context["external_user_id"],
            collection_key=collection_key,
            collection_name=collection_name,
            limit=limit,
        )

    def synchronize(self, **context: Any) -> dict[str, Any]:
        """Delta sync via Zotero library version cursor."""
        cursor_raw = context.get("sync_cursor") or ""
        since = 0
        try:
            parsed = json.loads(cursor_raw) if cursor_raw.strip().startswith("{") else {}
            since = int(parsed.get("library_version") or 0)
        except Exception:
            try:
                since = int(cursor_raw or 0)
            except (TypeError, ValueError):
                since = 0
        limit = int(context.get("limit") or 200)
        records, new_version = zotero_mod.fetch_items_since(
            context["access_token"],
            context["access_secret"],
            context["external_user_id"],
            since_version=since,
            limit=limit,
        )
        return {
            "records": records,
            "sync_cursor": json.dumps({"library_version": new_version}),
            "since": since,
            "fetched": len(records),
        }


class OpenAlexAdapter(ImportAdapter):
    """Maps a single Discover / Related work dict into LibraryRecord."""

    name: ClassVar[str] = "openalex"

    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        work = context.get("work") or {}
        if not work:
            return []
        title = (work.get("title") or "").strip()
        doi = (work.get("doi") or "").strip()
        if not title and not doi:
            return []
        year = work.get("year")
        return [
            LibraryRecord(
                title=title,
                authors=(work.get("authors") or "").strip(),
                year=str(year).strip()[:10] if year not in (None, "") else "",
                venue=(work.get("venue") or "").strip(),
                doi=doi,
                abstract=(work.get("abstract") or "").strip(),
                url=(work.get("open_access_url") or "").strip(),
                pdf_url=(work.get("open_access_url") or "").strip(),
                source="openalex",
                external_id=str(work.get("id") or work.get("paper_id") or ""),
                tags=["from-discover"] if not context.get("from_related") else ["from-related"],
            )
        ]


def get_adapter(name: str) -> ImportAdapter:
    from backend.library.adapters.mendeley_adapter import MendeleyAdapter

    registry: dict[str, type[ImportAdapter]] = {
        "bibtex": BibTeXAdapter,
        "ris": RISAdapter,
        "zotero": ZoteroAdapter,
        "openalex": OpenAlexAdapter,
        "mendeley": MendeleyAdapter,
    }
    key = (name or "").strip().lower()
    if key in {"bib", "biblatex"}:
        key = "bibtex"
    cls = registry.get(key)
    if not cls:
        raise KeyError(f"unknown_import_adapter:{name}")
    return cls()
