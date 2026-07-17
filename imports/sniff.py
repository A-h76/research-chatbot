def sniff_text(path: str, max_bytes: int = 2_000_000) -> str:
    """Best-effort: decode an unknown file as text; '' if it looks binary.
    The registry's fallback when no Importer's extension/mime matches."""
    with open(path, "rb") as f:
        raw = f.read(max_bytes)
    if not raw:
        return ""
    if b"\x00" in raw[:8192]:          # NUL byte => almost certainly binary
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="ignore")
