"""Minimal BibTeX parser/serializer — no third-party dependency."""

from __future__ import annotations

import re
from typing import Iterable

from .normalize import LibraryRecord, normalize_doi

_ENTRY_RE = re.compile(
    r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,]+)\s*,\s*(?P<body>.*?)\n\s*\}",
    re.DOTALL | re.IGNORECASE,
)
_FIELD_RE = re.compile(
    r"(?P<name>\w+)\s*=\s*(?:\{(?P<braced>.*?)\}|\"(?P<quoted>.*?)\")\s*,?",
    re.DOTALL,
)


def _unbrace(s: str) -> str:
    s = s.strip()
    # Collapse BibTeX braces used for case protection
    s = re.sub(r"[{}]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _authors_from_bibtex(raw: str) -> str:
    parts = [p.strip() for p in re.split(r"\s+and\s+", raw, flags=re.I) if p.strip()]
    return "; ".join(parts)


def _year_from_fields(fields: dict[str, str]) -> str:
    for key in ("year", "date"):
        v = fields.get(key, "")
        m = re.search(r"(19|20)\d{2}", v)
        if m:
            return m.group(0)
    return ""


def parse_bibtex(text: str) -> list[LibraryRecord]:
    if not text or not text.strip():
        return []
    records: list[LibraryRecord] = []
    for m in _ENTRY_RE.finditer(text):
        etype = m.group("type").lower()
        if etype in {"string", "preamble", "comment"}:
            continue
        fields: dict[str, str] = {}
        for fm in _FIELD_RE.finditer(m.group("body")):
            name = fm.group("name").lower()
            val = fm.group("braced") if fm.group("braced") is not None else fm.group("quoted")
            fields[name] = _unbrace(val or "")
        title = fields.get("title", "")
        doi = normalize_doi(fields.get("doi") or fields.get("DOI") or "")
        authors = _authors_from_bibtex(fields.get("author") or fields.get("editor") or "")
        venue = (
            fields.get("journal")
            or fields.get("booktitle")
            or fields.get("publisher")
            or fields.get("school")
            or ""
        )
        url = fields.get("url") or fields.get("howpublished") or ""
        if not title and not doi:
            continue
        records.append(
            LibraryRecord(
                title=title,
                authors=authors,
                year=_year_from_fields(fields),
                venue=venue,
                doi=doi,
                abstract=fields.get("abstract", ""),
                url=url,
                entry_type=etype,
                external_id=m.group("key").strip(),
                source="bibtex",
                tags=["from-bibtex"],
            )
        )
    return records


def _escape_bib(s: str) -> str:
    return (s or "").replace("{", "\\{").replace("}", "\\}")


def _cite_key(rec: LibraryRecord) -> str:
    if rec.external_id and re.match(r"^[\w:-]+$", rec.external_id):
        return rec.external_id
    first = (rec.authors or "anon").split(";")[0].split(",")[0].strip()
    key = "".join(ch for ch in first if ch.isalnum()).lower() + (rec.year or "")
    return key or "ref"


def to_bibtex(records: Iterable[LibraryRecord]) -> str:
    chunks: list[str] = []
    for rec in records:
        etype = rec.entry_type or "article"
        fields = []
        if rec.authors:
            fields.append(f"  author = {{{_escape_bib(rec.authors.replace(';', ' and'))}}}")
        if rec.title:
            fields.append(f"  title = {{{_escape_bib(rec.title)}}}")
        if rec.venue:
            journal_key = "booktitle" if etype in {"inproceedings", "incollection"} else "journal"
            fields.append(f"  {journal_key} = {{{_escape_bib(rec.venue)}}}")
        if rec.year:
            fields.append(f"  year = {{{_escape_bib(rec.year)}}}")
        if rec.doi:
            fields.append(f"  doi = {{{_escape_bib(rec.normalized_doi())}}}")
        if rec.url:
            fields.append(f"  url = {{{_escape_bib(rec.url)}}}")
        if rec.abstract:
            fields.append(f"  abstract = {{{_escape_bib(rec.abstract[:2000])}}}")
        chunks.append("@" + etype + "{" + _cite_key(rec) + ",\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(chunks) + ("\n" if chunks else "")
