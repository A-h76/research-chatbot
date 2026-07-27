"""RIS (Research Information Systems) parser/serializer."""

from __future__ import annotations

import re
from typing import Iterable

from .normalize import LibraryRecord, normalize_doi

# Common RIS type tags
_TYPE_MAP = {
    "JOUR": "article",
    "JFULL": "article",
    "BOOK": "book",
    "CHAP": "incollection",
    "CONF": "inproceedings",
    "CPAPER": "inproceedings",
    "THES": "phdthesis",
    "RPRT": "techreport",
    "GEN": "misc",
    "ELEC": "misc",
}


def _year_from(raw: str) -> str:
    m = re.search(r"(19|20)\d{2}", raw or "")
    return m.group(0) if m else ""


def parse_ris(text: str) -> list[LibraryRecord]:
    if not text or not text.strip():
        return []
    records: list[LibraryRecord] = []
    current: dict[str, list[str]] = {}
    etype = "article"

    def flush():
        nonlocal current, etype
        if not current:
            return
        title = (current.get("TI") or current.get("T1") or current.get("CT") or [""])[0]
        doi_raw = (current.get("DO") or current.get("DOI") or [""])[0]
        doi = normalize_doi(doi_raw)
        authors = "; ".join(current.get("AU", []) or current.get("A1", []))
        year = _year_from(
            (current.get("PY") or current.get("Y1") or current.get("DA") or [""])[0]
        )
        venue = (current.get("JO") or current.get("T2") or current.get("JF") or [""])[0]
        abstract = (current.get("AB") or current.get("N2") or [""])[0]
        url = (current.get("UR") or current.get("L1") or current.get("L2") or [""])[0]
        kw = current.get("KW") or []
        if title or doi:
            records.append(
                LibraryRecord(
                    title=title.strip(),
                    authors=authors,
                    year=year,
                    venue=venue.strip(),
                    doi=doi,
                    abstract=abstract.strip(),
                    url=url.strip(),
                    entry_type=etype,
                    source="ris",
                    tags=["from-ris"] + [f"kw:{k}" for k in kw[:10] if k],
                    pdf_url=(current.get("L1") or [""])[0].strip(),
                )
            )
        current = {}
        etype = "article"

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        # Tag is "XX  - value" (two spaces before dash) or "XX - value"
        m = re.match(r"^([A-Z0-9]{2})\s*-\s?(.*)$", line)
        if not m:
            # Continuation line for previous field
            if current:
                last_key = list(current.keys())[-1]
                current[last_key][-1] = (current[last_key][-1] + " " + line.strip()).strip()
            continue
        tag, value = m.group(1), m.group(2).strip()
        if tag == "TY":
            if current:
                flush()
            etype = _TYPE_MAP.get(value.upper(), "misc")
            current = {}
            continue
        if tag == "ER":
            flush()
            continue
        current.setdefault(tag, []).append(value)

    if current:
        flush()
    return records


_REV_TYPE = {
    "article": "JOUR",
    "book": "BOOK",
    "incollection": "CHAP",
    "inproceedings": "CONF",
    "phdthesis": "THES",
    "techreport": "RPRT",
}


def to_ris(records: Iterable[LibraryRecord]) -> str:
    chunks: list[str] = []
    for rec in records:
        lines = [f"TY  - {_REV_TYPE.get(rec.entry_type or 'article', 'GEN')}"]
        if rec.title:
            lines.append(f"TI  - {rec.title}")
        for author in [a.strip() for a in (rec.authors or "").split(";") if a.strip()]:
            lines.append(f"AU  - {author}")
        if rec.year:
            lines.append(f"PY  - {rec.year}")
        if rec.venue:
            lines.append(f"JO  - {rec.venue}")
        if rec.doi:
            lines.append(f"DO  - {rec.normalized_doi()}")
        if rec.url:
            lines.append(f"UR  - {rec.url}")
        if rec.abstract:
            lines.append(f"AB  - {rec.abstract[:4000]}")
        for tag in rec.tags:
            if tag.startswith("kw:"):
                lines.append(f"KW  - {tag[3:]}")
        lines.append("ER  - ")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks) + ("\n" if chunks else "")
