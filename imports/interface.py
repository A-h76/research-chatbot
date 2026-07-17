"""Importer interface — one class per format, each returning plain text
via the exact contract extract_text() has always had: '' for no readable
text, a bracketed '[...]' note when a format is recognised but can't be
parsed or isn't supported, or the extracted text otherwise."""

from typing import Protocol


class Importer(Protocol):
    extensions: tuple[str, ...]
    supports_locators: bool  # can chunk_document() attach page/section?

    def matches(self, lower_name: str, mime: str) -> bool: ...
    def extract(self, path: str, mime: str, name: str) -> str: ...
