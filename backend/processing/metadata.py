"""Rule-based metadata extraction (title, authors, venue, year, DOI,
abstract, keywords). Deterministic pattern matching only — no ML/LLM
call (see package docstring's Non-Goals and the project rule this task
was built under: "prefer deterministic rule-based classification first,
leave extension points for future ML/LLM classifiers"). Extension point:
MetadataExtractor.extract() is the one seam a future ML/LLM-backed
extractor would implement the same way (same input/output shape), so it
could be swapped in (or layered on top, filling in only the fields this
one left low-confidence) without touching callers.

Every regex/keyword list a heuristic depends on is a named module-level
constant, not a literal buried in a function body — the same "no
hardcoded constants" rule normalization.py's NORMALIZED_SECTIONS follows,
applied here to metadata patterns instead of section headings.
"""

import re
from typing import Optional

from .models import MetadataExtractionResult, ParsedPDF, SectionExtractionResult
from .normalization import normalize_heading

# DOIs are unambiguous enough that a regex match alone is high-confidence
# — this is the CrossRef-recommended DOI pattern (prefix "10." + registrant
# code + arbitrary suffix up to the next whitespace/quote/bracket).
_DOI_RE = re.compile(r'10\.\d{4,9}/[^\s"\'<>)\]]+')

# A bare 4-digit year, not part of a longer number (e.g. not the "2024" in
# "20241231" or a page number run). Restricted to a plausible publication
# range rather than any 4 digits, to cut down on false positives from
# random figures/statistics on the page.
_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")

# PDF metadata "creation date" is in the PDF spec's own D:YYYYMMDD... format.
_PDF_DATE_YEAR_RE = re.compile(r"D:(\d{4})")

# Substrings that mark a line as naming a publication venue. Checked as
# case-insensitive substrings of a line, not whole-line equality — real
# venue lines are rarely just the venue name on its own ("In Proceedings
# of the 40th International Conference on Machine Learning (ICML 2023)").
_VENUE_MARKERS: tuple[str, ...] = (
    "proceedings of",
    "journal of",
    "conference on",
    "transactions on",
    "in proceedings",
    "symposium on",
)

# Lines matching these (case-insensitive, anywhere in the line) precede a
# keyword list in most journal layouts.
_KEYWORDS_LABEL_RE = re.compile(r"(?:keywords|index terms)\s*[:\-]\s*(.+)", re.IGNORECASE)

# A line this short/long, or matching one of these patterns, is very
# unlikely to be a paper's title even if it's the first non-empty line —
# guards the title heuristic against picking up a running header/footer,
# a copyright notice, or a lone DOI/URL line instead.
_MIN_TITLE_LEN = 8
_MAX_TITLE_LEN = 250
_TITLE_REJECT_RE = re.compile(r"^(https?://|10\.\d{4,9}/|©|\(c\)|page \d+)", re.IGNORECASE)

# A line of comma/semicolon-separated "Firstname Lastname"-shaped tokens —
# the common byline layout directly under the title on page 1.
_AUTHOR_LINE_RE = re.compile(
    r"^([A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+)+)(\s*[,;]\s*[A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+)+)*$"
)


class MetadataExtractor:
    """Extracts bibliographic metadata from a parsed PDF using PDF-native
    metadata first, then heuristic pattern matching over page 1's text as
    a fallback for whatever the PDF's own metadata didn't have set."""

    def extract(
        self,
        parsed: ParsedPDF,
        sections: Optional[SectionExtractionResult] = None,
    ) -> MetadataExtractionResult:
        """`sections`, if the caller already ran SectionExtractor over the
        same document, lets the abstract come from that (more reliable —
        it uses the same multi-pattern heading detector every other
        section relies on) instead of this class's own simpler fallback
        heuristic. Optional: this class works standalone without it."""
        confidence: dict[str, float] = {}
        reasoning: dict[str, str] = {}

        title = self._extract_title(parsed, confidence, reasoning)
        authors = self._extract_authors(parsed, confidence, reasoning)
        venue = self._extract_venue(parsed, confidence, reasoning)
        year = self._extract_year(parsed, confidence, reasoning)
        doi = self._extract_doi(parsed, confidence, reasoning)
        abstract = self._extract_abstract(parsed, sections, confidence, reasoning)
        keywords = self._extract_keywords(parsed, confidence, reasoning)

        return MetadataExtractionResult(
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            doi=doi,
            abstract=abstract,
            keywords=keywords,
            confidence=confidence,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------ per-field
    def _extract_title(self, parsed: ParsedPDF, confidence: dict, reasoning: dict) -> str:
        native = (parsed.pdf_metadata.get("title") or "").strip()
        if native and len(native) >= _MIN_TITLE_LEN:
            confidence["title"] = 0.9
            reasoning["title"] = "from PDF metadata 'title' field"
            return native

        for line in self._page_one_lines(parsed):
            if _MIN_TITLE_LEN <= len(line) <= _MAX_TITLE_LEN and not _TITLE_REJECT_RE.match(line):
                confidence["title"] = 0.5
                reasoning["title"] = "heuristic: first substantial line on page 1"
                return line

        confidence["title"] = 0.0
        reasoning["title"] = "no PDF metadata title and no plausible title line found on page 1"
        return ""

    def _extract_authors(self, parsed: ParsedPDF, confidence: dict, reasoning: dict) -> list[str]:
        native = (parsed.pdf_metadata.get("author") or "").strip()
        if native:
            confidence["authors"] = 0.8
            reasoning["authors"] = "from PDF metadata 'author' field"
            return self._split_authors(native)

        for line in self._page_one_lines(parsed)[1:6]:
            if _AUTHOR_LINE_RE.match(line):
                confidence["authors"] = 0.4
                reasoning["authors"] = "heuristic: comma/semicolon-separated name-like line near top of page 1"
                return self._split_authors(line)

        confidence["authors"] = 0.0
        reasoning["authors"] = "no PDF metadata author and no name-like byline found on page 1"
        return []

    def _extract_venue(self, parsed: ParsedPDF, confidence: dict, reasoning: dict) -> str:
        for line in self._page_one_lines(parsed):
            lowered = line.lower()
            if any(marker in lowered for marker in _VENUE_MARKERS):
                confidence["venue"] = 0.5
                reasoning["venue"] = "heuristic: line contains a known venue marker phrase"
                return line

        subject = (parsed.pdf_metadata.get("subject") or "").strip()
        if subject:
            confidence["venue"] = 0.3
            reasoning["venue"] = "from PDF metadata 'subject' field (weak signal, not necessarily a venue)"
            return subject

        confidence["venue"] = 0.0
        reasoning["venue"] = "no venue marker phrase found on page 1 and no PDF metadata subject"
        return ""

    def _extract_year(self, parsed: ParsedPDF, confidence: dict, reasoning: dict) -> Optional[int]:
        creation_date = parsed.pdf_metadata.get("creationDate") or ""
        date_match = _PDF_DATE_YEAR_RE.match(creation_date)
        if date_match:
            confidence["year"] = 0.6
            reasoning["year"] = "from PDF metadata creation date"
            return int(date_match.group(1))

        year_match = _YEAR_RE.search(parsed.first_page_text)
        if year_match:
            confidence["year"] = 0.4
            reasoning["year"] = "heuristic: first plausible 4-digit year found on page 1"
            return int(year_match.group(1))

        confidence["year"] = 0.0
        reasoning["year"] = "no creation date in PDF metadata and no plausible year found on page 1"
        return None

    def _extract_doi(self, parsed: ParsedPDF, confidence: dict, reasoning: dict) -> Optional[str]:
        match = _DOI_RE.search(parsed.first_page_text) or _DOI_RE.search(parsed.raw_text)
        if match:
            confidence["doi"] = 0.95
            reasoning["doi"] = "regex match on standard DOI pattern"
            return match.group(0).rstrip(".")

        confidence["doi"] = 0.0
        reasoning["doi"] = "no DOI-shaped string found"
        return None

    def _extract_abstract(
        self,
        parsed: ParsedPDF,
        sections: Optional[SectionExtractionResult],
        confidence: dict,
        reasoning: dict,
    ) -> str:
        if sections is not None:
            found = sections.normalized_sections.get("abstract")
            if found:
                confidence["abstract"] = 0.9
                reasoning["abstract"] = "from SectionExtractor's detected 'abstract' section"
                return found.strip()

        lines = self._page_one_lines(parsed)
        for i, line in enumerate(lines):
            if normalize_heading(line).normalized_key == "abstract":
                body = "\n".join(lines[i + 1 :]).strip()
                if body:
                    confidence["abstract"] = 0.5
                    reasoning["abstract"] = "heuristic: text following an 'Abstract' line on page 1"
                    return body

        confidence["abstract"] = 0.0
        reasoning["abstract"] = "no abstract section detected and no 'Abstract' heading found on page 1"
        return ""

    def _extract_keywords(self, parsed: ParsedPDF, confidence: dict, reasoning: dict) -> list[str]:
        match = _KEYWORDS_LABEL_RE.search(parsed.first_page_text)
        if match:
            confidence["keywords"] = 0.6
            reasoning["keywords"] = "heuristic: text following a 'Keywords:'/'Index Terms:' label on page 1"
            raw = match.group(1).splitlines()[0]
            return [kw.strip() for kw in re.split(r"[;,]", raw) if kw.strip()]

        confidence["keywords"] = 0.0
        reasoning["keywords"] = "no 'Keywords:'/'Index Terms:' label found on page 1"
        return []

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _page_one_lines(parsed: ParsedPDF) -> list[str]:
        return [line.strip() for line in parsed.first_page_text.splitlines() if line.strip()]

    @staticmethod
    def _split_authors(raw: str) -> list[str]:
        parts = re.split(r"\s*;\s*|\s*,\s*(?=[A-Z])|\s+and\s+", raw.strip())
        return [p.strip() for p in parts if p.strip()]
