class XlsxImporter:
    extensions = (".xlsx", ".xlsm")
    supports_locators = False

    def matches(self, lower_name, mime):
        return lower_name.endswith((".xlsx", ".xlsm"))

    def extract(self, path, mime, name):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            parts = []
            for ws in wb.worksheets:
                parts.append(f"--- Sheet: {ws.title} ---")
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None]
                    if cells:
                        parts.append(" | ".join(cells))
            return "\n".join(parts).strip()
        finally:
            wb.close()
