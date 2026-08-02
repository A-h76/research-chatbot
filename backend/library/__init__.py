"""Library Bridge — BibTeX/RIS import-export, Connect Library (Zotero/Mendeley).

Never ``import server`` — factories take SessionLocal / models.

Phase 1a: ImportAdapter abstraction + one-shot connectors.
Phase 1b: incremental sync + PDF attachment (manual attach + ref-mgr pull).
Phase 1c: research readiness, library health, duplicate management.
"""

from .normalize import LibraryRecord, normalize_doi, title_year_key
from .bibtex import parse_bibtex, to_bibtex
from .ris import parse_ris, to_ris
from .collections import CollectionService
from .adapters import get_adapter
from .adapters.base import ImportAdapter, AdapterCapabilities

__all__ = [
    "LibraryRecord",
    "normalize_doi",
    "title_year_key",
    "parse_bibtex",
    "to_bibtex",
    "parse_ris",
    "to_ris",
    "CollectionService",
    "get_adapter",
    "ImportAdapter",
    "AdapterCapabilities",
]
