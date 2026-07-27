"""Real EPUB importer — parses the actual OCF/OPF structure (container.xml
-> package document -> spine) instead of falling through to ZipImporter's
generic "concatenate whatever extract_text() can read out of every zip
member" pass, which had no sense of reading order and pulled in
cover-image alt text, embedded font/CSS-adjacent junk, etc.

EPUB content documents are XHTML, which the spec requires to be
well-formed XML — stdlib xml.etree.ElementTree parses them directly, no
HTML-soup library needed (rung 3 of the ladder: stdlib does it). Some
real-world epubs still ship slightly malformed XHTML despite the spec; a
per-item parse failure is skipped, not fatal to the whole book, same
"degrade, don't crash" contract every other importer here follows.

Namespaces are matched by local tag name only (strip the `{uri}`
prefix), not the exact OPF/container URI — deliberately lenient, since
some real-world epub generators declare a slightly different or missing
namespace on these elements. Being strict would trade "works on the
epubs people actually have" for spec purity nothing here needs.
"""

import posixpath
import xml.etree.ElementTree as ET
import zipfile

_XHTML_SKIP_TAGS = {"script", "style"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _collect_text(elem, out: list) -> None:
    if _local(elem.tag).lower() in _XHTML_SKIP_TAGS:
        return
    if elem.text:
        out.append(elem.text)
    for child in elem:
        _collect_text(child, out)
        if child.tail:
            out.append(child.tail)


def _extract_document_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    out: list = []
    _collect_text(root, out)
    return " ".join(t.strip() for t in out if t and t.strip())


def _find_opf_path(zf: zipfile.ZipFile) -> str:
    data = zf.read("META-INF/container.xml")
    root = ET.fromstring(data)
    for elem in root.iter():
        if _local(elem.tag) == "rootfile":
            full_path = elem.get("full-path")
            if full_path:
                return full_path
    raise ValueError("no <rootfile> in META-INF/container.xml")


def _parse_opf(zf: zipfile.ZipFile, opf_path: str):
    """Returns (manifest: {id: zip-member-path}, spine_idrefs: [id, ...]),
    spine in reading order."""
    root = ET.fromstring(zf.read(opf_path))
    opf_dir = posixpath.dirname(opf_path)

    manifest = {}
    spine_idrefs = []
    for elem in root.iter():
        local = _local(elem.tag)
        if local == "item":
            item_id, href = elem.get("id"), elem.get("href")
            if item_id and href:
                member = posixpath.normpath(posixpath.join(opf_dir, href)) if opf_dir else href
                manifest[item_id] = member
        elif local == "itemref":
            idref = elem.get("idref")
            if idref:
                spine_idrefs.append(idref)

    return manifest, spine_idrefs


class EpubImporter:
    extensions = (".epub",)
    supports_locators = False

    def matches(self, lower_name, mime):
        return lower_name.endswith(".epub") or "epub" in (mime or "")

    def extract(self, path, mime, name):
        try:
            zf = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            return "[extraction failed: not a valid epub archive]"

        with zf:
            try:
                opf_path = _find_opf_path(zf)
                manifest, spine_idrefs = _parse_opf(zf, opf_path)
            except Exception as e:
                return f"[extraction failed: could not read epub package document ({e})]"

            parts = []
            for idref in spine_idrefs:
                member = manifest.get(idref)
                if not member:
                    continue
                try:
                    xml_bytes = zf.read(member)
                except KeyError:
                    continue
                text = _extract_document_text(xml_bytes)
                if text:
                    parts.append(text)

        full_text = "\n\n".join(parts).strip()
        return full_text if full_text else "[no readable text found in epub]"
