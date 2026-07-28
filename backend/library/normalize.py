"""Normalized bibliographic record shared by BibTeX, RIS, and Connect imports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>)\]]+", re.I)
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_doi(raw: str | None) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
        "DOI:",
    ):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix) :]
            break
    m = _DOI_RE.search(s)
    return (m.group(0) if m else s).rstrip(".,;)").strip()


def title_year_key(title: str | None, year: str | None) -> str:
    t = _PUNCT_RE.sub("", _WS_RE.sub(" ", (title or "").strip().lower())).strip()
    y = (year or "").strip()[:4]
    if not t:
        return ""
    return f"{t}|{y}" if y else t


@dataclass
class LibraryRecord:
    """Provider-agnostic paper metadata for import."""

    title: str = ""
    authors: str = ""  # "Last, F.; Last, F."
    year: str = ""
    venue: str = ""
    doi: str = ""
    abstract: str = ""
    url: str = ""
    entry_type: str = "article"  # article|book|inproceedings|…
    external_id: str = ""  # Zotero item key, Mendeley id, etc.
    source: str = "bibtex"  # bibtex|ris|zotero|mendeley
    tags: list[str] = field(default_factory=list)
    pdf_url: str = ""
    collection_keys: list[str] = field(default_factory=list)  # Zotero collection keys
    collection_name: str = ""  # hint when importing a single folder

    def normalized_doi(self) -> str:
        return normalize_doi(self.doi)

    def dedupe_key(self) -> str:
        doi = self.normalized_doi()
        if doi:
            return f"doi:{doi.lower()}"
        ty = title_year_key(self.title, self.year)
        if ty:
            return f"ty:{ty}"
        if self.external_id:
            return f"ext:{self.source}:{self.external_id}"
        return ""

    def display_name(self) -> str:
        return (self.title or self.normalized_doi() or "imported-paper")[:300]
