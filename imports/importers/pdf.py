class PdfImporter:
    extensions = (".pdf",)
    supports_locators = True

    def matches(self, lower_name, mime):
        return lower_name.endswith(".pdf") or "pdf" in (mime or "")

    def extract(self, path, mime, name):
        """NUL-sentinel page markers for locators — each page is prefixed
        with \\x00PAGE<n>\\x00 so chunk_document() can annotate every chunk
        with its 1-based page number."""
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        try:
            parts = []
            for i, page in enumerate(doc, 1):
                txt = page.get_text()
                if txt.strip():
                    parts.append(f"\x00PAGE{i}\x00\n{txt}")
            return "\n\n".join(parts).strip()
        finally:
            doc.close()
