import os
import tempfile
import zipfile


class ZipImporter:
    """Recursively pulls readable text out of an archive's members,
    dispatching each member back through the registry."""
    extensions = (".zip",)
    supports_locators = False

    def matches(self, lower_name, mime):
        return lower_name.endswith(".zip") or "zip" in (mime or "")

    def extract(self, path, mime, name, depth=0):
        # Deferred import: the registry constructs this importer at module
        # load time, so importing the registry back here at load time
        # would be circular. Resolved fine at call time, once both modules
        # have finished loading — same shape as the original _extract_zip's
        # forward reference to extract_text (defined later in server.py).
        from imports.registry import extract_text

        if depth > 2:
            return ""
        parts = []
        try:
            zf = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            return "[extraction failed: not a valid zip archive]"
        with zf:
            for info in zf.infolist():
                member = info.filename
                base = os.path.basename(member)
                if info.is_dir() or not base or base.startswith(".") \
                        or "__MACOSX" in member:
                    continue
                if info.file_size > 25 * 1024 * 1024:          # skip huge members
                    continue
                try:
                    data = zf.read(info)
                except Exception:
                    continue
                ext = os.path.splitext(base)[1] or ".bin"
                fd, tmp = tempfile.mkstemp(suffix=ext)
                try:
                    with os.fdopen(fd, "wb") as tf:
                        tf.write(data)
                    sub = (self.extract(tmp, None, member, depth + 1)
                           if ext.lower() == ".zip"
                           else extract_text(tmp, None, member))
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                if sub and not sub.startswith("["):
                    parts.append(f"\n===== {member} =====\n{sub}")
        return "\n".join(parts).strip()
