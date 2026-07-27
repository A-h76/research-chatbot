"""ImportAdapter — formal entry for all library connectors.

Phase 1a: authenticate (where needed) + fetch_records → LibraryImportService.
Phase 1b: synchronize() incremental delta + PDF attach (import_files / attach route).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from backend.library.normalize import LibraryRecord


@dataclass(frozen=True)
class AdapterCapabilities:
    """What this adapter supports today."""

    oauth: bool = False
    file_parse: bool = False
    folder_list: bool = False
    incremental_sync: bool = False  # Phase 1b
    file_import: bool = False  # Phase 1b — PDF attachments


class ImportAdapter(ABC):
    """One connector → list[LibraryRecord] → shared import pipeline."""

    name: ClassVar[str] = "base"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities()

    def configured(self) -> bool:
        """False when server credentials / env are missing."""
        return True

    @abstractmethod
    def fetch_records(self, **context: Any) -> list[LibraryRecord]:
        """Return normalized metadata records (one-shot for Phase 1a)."""

    def list_folders(self, **context: Any) -> list[dict[str, Any]]:
        """Optional folder/collection listing for Connect UIs."""
        raise NotImplementedError(f"{self.name} does not list folders")

    def synchronize(self, **context: Any) -> dict[str, Any]:
        """Phase 1b — incremental sync. Not available in Phase 1a."""
        raise NotImplementedError(
            f"{self.name}: incremental sync is Phase 1b (not Phase 1a)"
        )

    def import_files(self, **context: Any) -> dict[str, Any]:
        """Phase 1b — attach/download PDFs into Research Assets."""
        raise NotImplementedError(
            f"{self.name}: PDF file import is Phase 1b (not Phase 1a)"
        )
