"""Document quality assessment — OCR/extraction-completeness signals and
missing-section detection. Deterministic, rule-based (see package
docstring): every signal here is a plain arithmetic/threshold check over
already-extracted facts (ParsedPDF, SectionExtractionResult), never a
model call.
"""

import re

from .models import DocumentQuality, ParsedPDF, SectionExtractionResult

# Sections a typical academic paper is expected to have — this list, not
# NORMALIZED_SECTIONS' full key set, drives missing_sections/has_* below.
# ("introduction"/"references"/"acknowledgments"/"appendix" are real,
# normalizable sections too, just not ones DocumentQuality's own has_*
# fields track — extend this tuple, not the has_* fields, if a future
# document type needs a different expected-sections baseline.)
_EXPECTED_CORE_SECTIONS: tuple[str, ...] = ("abstract", "methods", "results", "discussion")

# Rough plausible words-per-page for a normal (non-scanned, cleanly
# extracted) academic paper. Below this, extraction likely lost content
# (broken text layer, heavy figure/table density misread as sparse text,
# etc.) even though *some* text did come through.
_EXPECTED_WORDS_PER_PAGE = 150

# A run of the Unicode replacement character, or other control characters
# that have no business appearing in real body text, is a strong signal
# the text layer is OCR noise / a broken encoding rather than genuine text.
_GARBLED_CHAR_RE = re.compile(r"[�\x00-\x08\x0b\x0c\x0e-\x1f]")


class QualityAssessor:
    """Assesses a parsed, section-extracted document for OCR/extraction
    quality and structural completeness."""

    def assess(self, parsed: ParsedPDF, sections: SectionExtractionResult) -> DocumentQuality:
        word_count = len(parsed.raw_text.split())

        ocr_quality = self._assess_ocr_quality(parsed)
        text_extraction_quality = self._assess_extraction_quality(parsed, word_count)

        has_abstract = "abstract" in sections.normalized_sections
        has_methods = "methods" in sections.normalized_sections
        has_results = "results" in sections.normalized_sections
        has_discussion = "discussion" in sections.normalized_sections
        has_references = "references" in sections.normalized_sections

        present = {
            "abstract": has_abstract,
            "methods": has_methods,
            "results": has_results,
            "discussion": has_discussion,
        }
        missing_sections = [name for name in _EXPECTED_CORE_SECTIONS if not present.get(name, False)]

        warnings: list[str] = []
        errors: list[str] = []
        self._collect_messages(parsed, missing_sections, warnings, errors)

        section_completeness = 1.0 - (len(missing_sections) / len(_EXPECTED_CORE_SECTIONS))
        confidence = (ocr_quality + text_extraction_quality + section_completeness) / 3

        return DocumentQuality(
            ocr_quality=ocr_quality,
            text_extraction_quality=text_extraction_quality,
            missing_sections=missing_sections,
            has_references=has_references,
            has_abstract=has_abstract,
            has_methods=has_methods,
            has_results=has_results,
            has_discussion=has_discussion,
            confidence=confidence,
            warnings=warnings,
            errors=errors,
        )

    # ------------------------------------------------------------ signals
    @staticmethod
    def _assess_ocr_quality(parsed: ParsedPDF) -> float:
        """1.0 = clean digital text; lower values mean the source looks
        scanned/image-based or the text layer looks garbled. Does not
        perform OCR itself (see package Non-Goals) — this only decides
        how much to trust the text extraction already has."""
        if parsed.is_likely_scanned:
            return 0.0

        if parsed.page_count == 0:
            return 0.0

        page_ratio = parsed.text_page_count / parsed.page_count

        garbled_matches = len(_GARBLED_CHAR_RE.findall(parsed.raw_text))
        garbled_ratio = garbled_matches / max(len(parsed.raw_text), 1)
        garbled_penalty = min(garbled_ratio * 50, 1.0)  # a few garbled chars matter a lot; scaled deliberately steep

        return max(0.0, page_ratio - garbled_penalty)

    @staticmethod
    def _assess_extraction_quality(parsed: ParsedPDF, word_count: int) -> float:
        """1.0 = word count plausible for the page count; scales down for
        text that looks truncated/sparse relative to how many pages
        supposedly produced it."""
        if parsed.text_page_count == 0:
            return 0.0
        words_per_page = word_count / parsed.text_page_count
        return min(words_per_page / _EXPECTED_WORDS_PER_PAGE, 1.0)

    @staticmethod
    def _collect_messages(
        parsed: ParsedPDF,
        missing_sections: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        if parsed.is_likely_scanned:
            errors.append(
                f"No extractable text found on any of {parsed.page_count} page(s) — "
                "this document may be a scanned/image-only PDF."
            )
        elif not parsed.raw_text.strip():
            errors.append("No extractable text found in this document.")
        elif parsed.text_page_count < parsed.page_count:
            warnings.append(f"Only {parsed.text_page_count} of {parsed.page_count} page(s) contained extractable text.")

        for section in missing_sections:
            warnings.append(f"No '{section}' section detected.")
