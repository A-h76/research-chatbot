class LegacyOfficeImporter:
    """.doc/.ppt/.xls — the old binary Office formats. Not parsed (neither
    python-docx/pptx/openpyxl nor PyMuPDF read the pre-XML binary format);
    returns a note telling the user how to get a format that is."""

    extensions = (".doc", ".ppt", ".xls")
    supports_locators = False

    def matches(self, lower_name, mime):
        return lower_name.endswith(self.extensions)

    def extract(self, path, mime, name):
        return (
            "[legacy Microsoft Office binary format — ask the user to "
            "re-save it as .docx / .pptx / .xlsx or export to PDF]"
        )
