"""Library Bridge — BibTeX/RIS import-export, Connect Library (Zotero/Mendeley).

Never ``import server`` — factories take SessionLocal / models.
"""

from .normalize import LibraryRecord, normalize_doi, title_year_key
from .bibtex import parse_bibtex, to_bibtex
from .ris import parse_ris, to_ris
from .collections import CollectionService

__all__ = [
    "LibraryRecord",
    "normalize_doi",
    "title_year_key",
    "parse_bibtex",
    "to_bibtex",
    "parse_ris",
    "to_ris",
    "CollectionService",
]
